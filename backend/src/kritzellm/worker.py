"""The background worker: `python -m kritzellm.worker`.

It runs queued jobs one at a time, oldest first. A `NOTIFY` wakes it as soon as jobs are queued;
it also polls every few seconds in case one was missed. A job that was running when the worker
stopped is queued again on the next start, which is safe because there's only ever one worker.
"""

import asyncio
import contextlib
import logging
import signal
import time
from collections.abc import Awaitable, Callable
from types import TracebackType
from typing import Self

from sqlalchemy.ext.asyncio import AsyncSession

from kritzellm.api.schemas.common import Problem
from kritzellm.api.schemas.jobs import JobKind
from kritzellm.api.schemas.pages import PageStatus
from kritzellm.config import Settings, get_settings
from kritzellm.core import jobs
from kritzellm.core import pages as core_pages
from kritzellm.db import create_engine, create_sessionmaker
from kritzellm.db import models as db

# Named explicitly: under `python -m` this module is `__main__`.
logger = logging.getLogger("kritzellm.worker")

POLL_SECONDS = 5.0
"""How long to sleep without a `NOTIFY` before looking for queued jobs anyway."""

Handler = Callable[[AsyncSession, db.Job], Awaitable[None]]


async def ingest_page(session: AsyncSession, job: db.Job) -> None:
    """Walks a new page through its statuses. A placeholder until pages are transcribed."""
    assert job.page_id is not None
    steps = (PageStatus.TRANSCRIBING, PageStatus.INDEXING)
    for done, status in enumerate(steps):
        if not await core_pages.set_status(session, job.page_id, status):
            return  # The page was deleted, and its job with it.
        await jobs.set_progress(session, job.id, done, len(steps))
        await session.commit()
    await core_pages.set_status(session, job.page_id, PageStatus.READY)
    await jobs.set_progress(session, job.id, len(steps), len(steps))


HANDLERS: dict[JobKind, Handler] = {JobKind.INGEST_PAGE: ingest_page}


def _problem(exc: Exception) -> dict[str, object]:
    detail = str(exc) or type(exc).__name__
    return Problem(title="Job failed", status=500, detail=detail).model_dump(
        mode="json", exclude_none=True
    )


class Worker:
    """Runs jobs against the configured database. Use it as an `async with` block."""

    def __init__(self, settings: Settings) -> None:
        self.engine = create_engine(settings)
        self.sessionmaker = create_sessionmaker(self.engine)
        self._wakeup = asyncio.Event()

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
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
                handler = HANDLERS.get(kind)
                if handler is None:
                    raise NotImplementedError(f"{kind} jobs aren't built yet")
                await handler(session, job)
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


async def main() -> None:
    task = asyncio.current_task()
    assert task is not None
    loop = asyncio.get_running_loop()
    for stop in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(stop, task.cancel)
    async with Worker(get_settings()) as worker:
        try:
            await worker.run()
        except asyncio.CancelledError:
            logger.info("Stopped")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s [%(name)s] %(message)s")
    asyncio.run(main())
