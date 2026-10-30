"""The background worker: `python -m kritzellm.worker`.

It runs queued jobs one at a time, oldest first. A `NOTIFY` wakes it as soon as jobs are queued;
it also polls every few seconds in case one was missed. A job that was running when the worker
stopped is queued again on the next start, which is safe because there's only ever one worker.

`python -m kritzellm.worker healthcheck` exits non-zero unless the worker's heartbeat is fresh.
"""

import asyncio
import contextlib
import logging
import signal
import sys
import tempfile
import time
from collections.abc import Awaitable, Callable
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession

from kritzellm.api.schemas.common import Problem
from kritzellm.api.schemas.jobs import JobKind
from kritzellm.api.schemas.pages import ImageVariant, PageStatus
from kritzellm.config import Settings, get_settings
from kritzellm.core import indexing, jobs
from kritzellm.core import pages as core_pages
from kritzellm.core.storage import variant_path
from kritzellm.core.transcribe import transcribe
from kritzellm.db import create_engine, create_sessionmaker
from kritzellm.db import models as db

# Named explicitly: under `python -m` this module is `__main__`.
logger = logging.getLogger("kritzellm.worker")

POLL_SECONDS = 5.0
"""How long to sleep without a `NOTIFY` before looking for queued jobs anyway."""

HEARTBEAT_FILE = Path(tempfile.gettempdir()) / "kritzellm-worker.heartbeat"
"""Touched regularly while the worker's event loop runs, so a healthcheck can tell it's alive."""
HEARTBEAT_SECONDS = 10.0
HEARTBEAT_MAX_AGE_SECONDS = 30.0

Handler = Callable[[AsyncSession, db.Job, Settings], Awaitable[None]]

READ_STEPS = 2
"""Transcribing, then indexing."""


async def read_page(session: AsyncSession, job: db.Job, settings: Settings) -> None:
    """Reads a page into blocks (afresh, if it was read before), then indexes them."""
    job_id, page_id = job.id, job.page_id
    assert page_id is not None
    page = await session.get(db.Page, page_id)
    if page is None:
        return  # The page was deleted, and its job with it.
    image_path = variant_path(
        settings.data_dir, page_id, ImageVariant.NORMALIZED, page.original_media_type
    )
    await core_pages.set_status(session, page_id, PageStatus.TRANSCRIBING)
    await jobs.set_progress(session, job_id, 0, READ_STEPS)
    await session.commit()

    image = await asyncio.to_thread(image_path.read_bytes)
    transcription = await transcribe(image, settings)
    model = settings.transcribe_model
    if not await core_pages.save_transcription(session, page_id, transcription, model):
        return
    await _index(session, job_id, page_id, settings, done=1, total=READ_STEPS)


async def reindex_page(session: AsyncSession, job: db.Job, settings: Settings) -> None:
    """Indexes a page again after its blocks were edited."""
    assert job.page_id is not None
    await _index(session, job.id, job.page_id, settings, done=0, total=1)


async def _index(
    session: AsyncSession, job_id: str, page_id: str, settings: Settings, *, done: int, total: int
) -> None:
    """The last step of a page job: chunking and embedding its blocks for search."""
    if not await core_pages.set_status(session, page_id, PageStatus.INDEXING):
        return
    await jobs.set_progress(session, job_id, done, total)
    await session.commit()

    if not await indexing.index_page(session, page_id, settings):
        return
    await core_pages.set_status(session, page_id, PageStatus.READY)
    await jobs.set_progress(session, job_id, total, total)


async def reindex_all(session: AsyncSession, job: db.Job, settings: Settings) -> None:
    """Indexes every ready page again, e.g. after switching `EMBED_MODEL`.

    Each page is saved on its own and stays `ready` throughout, keeping its old chunks until the
    new ones are in.
    """
    job_id = job.id
    page_ids = await indexing.ready_page_ids(session)
    await jobs.set_progress(session, job_id, 0, len(page_ids))
    await session.commit()
    for done, page_id in enumerate(page_ids, start=1):
        await indexing.index_page(session, page_id, settings)
        await jobs.set_progress(session, job_id, done, len(page_ids))
        await session.commit()


HANDLERS: dict[JobKind, Handler] = {
    JobKind.INGEST_PAGE: read_page,
    JobKind.TRANSCRIBE_PAGE: read_page,
    JobKind.REINDEX_PAGE: reindex_page,
    JobKind.REINDEX_ALL: reindex_all,
}


def _problem(exc: Exception) -> dict[str, object]:
    detail = str(exc) or type(exc).__name__
    return Problem(title="Job failed", status=500, detail=detail).model_dump(
        mode="json", exclude_none=True
    )


class Worker:
    """Runs jobs against the configured database. Use it as `async with aclosing(Worker(…))`."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.engine = create_engine(settings)
        self.sessionmaker = create_sessionmaker(self.engine)
        self._wakeup = asyncio.Event()

    async def aclose(self) -> None:
        await self.engine.dispose()

    async def run(self) -> None:
        """Works through jobs until cancelled."""
        await self._requeue_interrupted()
        async with self.engine.connect() as connection:
            listener = (await connection.get_raw_connection()).driver_connection
            assert listener is not None
            await listener.add_listener(jobs.CHANNEL, self._notified)
            logger.info("Waiting for jobs")
            while True:
                self._wakeup.clear()
                while await self.run_next():
                    pass
                with contextlib.suppress(TimeoutError):
                    async with asyncio.timeout(POLL_SECONDS):
                        await self._wakeup.wait()

    async def run_until_idle(self) -> None:
        """Starts like `run`, but returns once no jobs are queued."""
        await self._requeue_interrupted()
        while await self.run_next():
            pass

    async def run_next(self) -> bool:
        """Runs the oldest queued job. `False` if there was none."""
        async with self.sessionmaker() as session:
            job = await jobs.claim_next(session)
            await session.commit()
            if job is None:
                return False

            # A rollback expires `job`, so keep what the failure handling needs.
            job_id, kind, page_id = job.id, job.kind, job.page_id
            logger.info("Running %s job %s", kind, job_id)
            started = time.perf_counter()
            try:
                await HANDLERS[kind](session, job, self.settings)
                await jobs.succeed(session, job_id)
                await session.commit()
            except Exception as exc:
                logger.exception("%s job %s failed", kind, job_id)
                await session.rollback()
                problem = _problem(exc)
                await jobs.fail(session, job_id, problem)
                if page_id is not None:
                    await core_pages.set_status(session, page_id, PageStatus.FAILED, error=problem)
                await session.commit()
            else:
                elapsed = time.perf_counter() - started
                logger.info("Finished %s job %s in %.1fs", kind, job_id, elapsed)
        return True

    async def _requeue_interrupted(self) -> None:
        async with self.sessionmaker() as session:
            if count := await jobs.requeue_interrupted(session):
                logger.warning("Queued %d interrupted job(s) again", count)
            await session.commit()

    def _notified(self, *_: object) -> None:
        self._wakeup.set()


async def heartbeat() -> None:
    """Touches `HEARTBEAT_FILE` until cancelled. It stops when the event loop is stuck."""
    while True:
        await asyncio.to_thread(HEARTBEAT_FILE.touch)
        await asyncio.sleep(HEARTBEAT_SECONDS)


def is_alive() -> bool:
    """Whether a worker touched the heartbeat file recently."""
    try:
        age = time.time() - HEARTBEAT_FILE.stat().st_mtime
    except FileNotFoundError:
        return False
    return age < HEARTBEAT_MAX_AGE_SECONDS


async def main() -> None:
    task = asyncio.current_task()
    assert task is not None
    loop = asyncio.get_running_loop()
    for stop in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(stop, task.cancel)
    beating = asyncio.create_task(heartbeat())
    async with contextlib.aclosing(Worker(get_settings())) as worker:
        try:
            await worker.run()
        except asyncio.CancelledError:
            logger.info("Stopped")
        finally:
            beating.cancel()


if __name__ == "__main__":
    if sys.argv[1:] == ["healthcheck"]:
        sys.exit(0 if is_alive() else 1)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s [%(name)s] %(message)s")
    asyncio.run(main())
