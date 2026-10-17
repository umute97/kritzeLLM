import asyncio
import contextlib
import os
import time
from collections.abc import Callable
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from pydantic import PostgresDsn
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from kritzellm import worker as worker_module
from kritzellm.api.schemas.jobs import JobKind, JobStatus
from kritzellm.config import Settings
from kritzellm.core import jobs
from kritzellm.core.storage import Staging
from kritzellm.db import models as db
from kritzellm.ids import Prefix, new_id
from kritzellm.worker import Worker

pytestmark = pytest.mark.db

MakeImage = Callable[..., bytes]


def _journal(client: TestClient) -> str:
    response = client.post("/journals", json={"name": "Jobs"})
    assert response.status_code == 201, response.text
    return response.json()["id"]


def _upload(client: TestClient, journal_id: str, *images: bytes) -> list[dict]:
    response = client.post(
        f"/journals/{journal_id}/pages",
        files=[
            ("files", (f"{index}.jpg", image, "image/jpeg")) for index, image in enumerate(images)
        ],
    )
    assert response.status_code == 201, response.text
    return response.json()["items"]


def _job(client: TestClient, job_id: str) -> dict:
    response = client.get(f"/jobs/{job_id}")
    assert response.status_code == 200, response.text
    return response.json()


def _page(client: TestClient, page_id: str) -> dict:
    response = client.get(f"/pages/{page_id}")
    assert response.status_code == 200, response.text
    return response.json()


@pytest.fixture
def settings(database_url: str, data_dir: Path) -> Settings:
    return Settings(api_token=None, database_url=PostgresDsn(database_url), data_dir=data_dir)


@pytest.fixture
def work(settings: Settings) -> Callable[[], None]:
    """Runs the worker until no jobs are queued."""

    async def run() -> None:
        async with Worker(settings) as worker:
            await worker.run_until_idle()

    return lambda: asyncio.run(run())


def test_upload_queues_an_ingest_job_per_new_page(
    db_client: TestClient, make_image: MakeImage
) -> None:
    items = _upload(db_client, _journal(db_client), make_image(color="red"))

    job = items[0]["job"]
    assert job["id"].startswith("job_")
    assert job["kind"] == "ingestPage"
    assert job["status"] == "queued"
    assert job["target"] == {"type": "page", "id": items[0]["page"]["id"]}
    assert (job["progress"], job["error"], job["resultUrl"]) == (None, None, None)
    assert (job["startedAt"], job["finishedAt"]) == (None, None)
    assert _job(db_client, job["id"]) == job


def test_a_duplicate_gets_the_pages_latest_job(
    db_client: TestClient, make_image: MakeImage
) -> None:
    journal_id = _journal(db_client)
    photo = make_image(color="blue")
    first = _upload(db_client, journal_id, photo)[0]

    again, twice = _upload(db_client, journal_id, photo, photo)

    assert again["duplicate"]
    assert twice["duplicate"]
    assert again["job"]["id"] == twice["job"]["id"] == first["job"]["id"]


def test_the_worker_walks_the_page_to_ready(
    db_client: TestClient, make_image: MakeImage, work: Callable[[], None]
) -> None:
    (item,) = _upload(db_client, _journal(db_client), make_image(color="green"))

    work()

    job = _job(db_client, item["job"]["id"])
    assert job["status"] == "succeeded"
    assert job["progress"] == {"done": 2, "total": 2}
    assert job["error"] is None
    assert job["createdAt"] <= job["startedAt"] <= job["finishedAt"]
    page = _page(db_client, item["page"]["id"])
    assert (page["status"], page["error"]) == ("ready", None)


def test_a_failing_job_fails_its_page(
    db_client: TestClient,
    make_image: MakeImage,
    work: Callable[[], None],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def boom(session: AsyncSession, job: db.Job) -> None:
        raise RuntimeError("The pen ran out of ink")

    monkeypatch.setitem(worker_module.HANDLERS, JobKind.INGEST_PAGE, boom)
    (item,) = _upload(db_client, _journal(db_client), make_image(color="purple"))

    work()

    job = _job(db_client, item["job"]["id"])
    assert job["status"] == "failed"
    assert job["finishedAt"] is not None
    error = job["error"]
    assert (error["title"], error["status"]) == ("Job failed", 500)
    assert error["detail"] == "The pen ran out of ink"
    page = _page(db_client, item["page"]["id"])
    assert (page["status"], page["error"]) == ("failed", job["error"])


def test_kinds_without_a_handler_fail(
    db_client: TestClient, settings: Settings, work: Callable[[], None]
) -> None:
    async def queue() -> str:
        engine = create_async_engine(str(settings.database_url))
        async with AsyncSession(engine, expire_on_commit=False) as session:
            job = await jobs.enqueue(session, JobKind.REINDEX_ALL)
            await session.commit()
        await engine.dispose()
        return job.id

    job_id = asyncio.run(queue())
    assert _job(db_client, job_id)["target"] == {"type": "all", "id": None}

    work()

    job = _job(db_client, job_id)
    assert job["status"] == "failed"
    assert job["error"]["detail"] == "reindexAll jobs aren't built yet"


def test_interrupted_jobs_run_again(
    db_client: TestClient, make_image: MakeImage, settings: Settings, work: Callable[[], None]
) -> None:
    (item,) = _upload(db_client, _journal(db_client), make_image(color="orange"))
    job_id = item["job"]["id"]

    async def interrupt() -> None:
        engine = create_async_engine(str(settings.database_url))
        async with engine.begin() as connection:
            await connection.execute(
                update(db.Job)
                .where(db.Job.id == job_id)
                .values(status=JobStatus.RUNNING, progress_done=1, progress_total=2)
            )
        await engine.dispose()

    asyncio.run(interrupt())
    assert _job(db_client, job_id)["status"] == "running"

    work()

    assert _job(db_client, job_id)["status"] == "succeeded"


def test_deleting_a_page_deletes_its_jobs(
    db_client: TestClient, make_image: MakeImage, work: Callable[[], None]
) -> None:
    (item,) = _upload(db_client, _journal(db_client), make_image(color="yellow"))

    assert db_client.delete(f"/pages/{item['page']['id']}").status_code == 204
    assert db_client.get(f"/jobs/{item['job']['id']}").status_code == 404
    work()  # Nothing left to trip over.


def test_a_failed_upload_leaves_no_pages_files_or_jobs(
    db_client: TestClient,
    make_image: MakeImage,
    data_dir: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    journal_id = _journal(db_client)
    publish = Staging.publish
    calls = []

    def flaky_publish(self: Staging, staged: Path, page_id: str) -> None:
        calls.append(page_id)
        if len(calls) == 2:
            raise OSError("Disk full")
        publish(self, staged, page_id)

    monkeypatch.setattr(Staging, "publish", flaky_publish)
    with pytest.raises(OSError, match="Disk full"):
        _upload(db_client, journal_id, make_image(color="red"), make_image(color="blue"))

    assert db_client.get(f"/pages?journalId={journal_id}").json()["items"] == []
    assert not (data_dir / "pages").exists() or not any((data_dir / "pages").iterdir())
    listed = {job["target"]["id"] for job in db_client.get("/jobs?limit=100").json()["items"]}
    assert listed.isdisjoint(calls)


def test_list_is_newest_first_and_pages(db_client: TestClient, make_image: MakeImage) -> None:
    items = _upload(
        db_client,
        _journal(db_client),
        *(make_image(color=color) for color in ("navy", "teal", "olive")),
    )
    ours = [item["job"]["id"] for item in reversed(items)]

    seen, cursor = [], None
    while True:
        params = {"limit": 2} | ({"cursor": cursor} if cursor else {})
        body = db_client.get("/jobs", params=params).json()
        seen += [job["id"] for job in body["items"]]
        cursor = body["nextCursor"]
        if cursor is None or set(ours) <= set(seen):
            break

    assert seen[: len(ours)] == ours


def test_list_filters(
    db_client: TestClient, make_image: MakeImage, work: Callable[[], None]
) -> None:
    (done,) = _upload(db_client, _journal(db_client), make_image(color=(1, 2, 3)))
    work()
    (queued,) = _upload(db_client, _journal(db_client), make_image(color=(3, 2, 1)))

    def ids(**params: str) -> set[str]:
        response = db_client.get("/jobs", params={"limit": "100", **params})
        assert response.status_code == 200, response.text
        return {job["id"] for job in response.json()["items"]}

    assert queued["job"]["id"] in ids(status="queued")
    assert done["job"]["id"] not in ids(status="queued")
    assert done["job"]["id"] in ids(status="succeeded", kind="ingestPage")
    assert not ids(kind="exportJournal")


def test_unknown_job_is_404(db_client: TestClient) -> None:
    response = db_client.get(f"/jobs/{new_id(Prefix.JOB)}")
    assert response.status_code == 404
    assert response.json()["detail"] == "Job not found."


def test_the_worker_wakes_up_for_new_jobs(
    settings: Settings, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A queued job runs right away, long before the worker would poll again."""
    monkeypatch.setattr(worker_module, "POLL_SECONDS", 60.0)

    async def scenario() -> JobStatus | None:
        engine = create_async_engine(str(settings.database_url))
        async with (
            Worker(settings) as worker,
            AsyncSession(engine, expire_on_commit=False) as session,
        ):
            running = asyncio.create_task(worker.run())
            await asyncio.sleep(0.5)  # Let it catch up and go to sleep.
            job = await jobs.enqueue(session, JobKind.REINDEX_ALL)
            await session.commit()
            status_query = select(db.Job.status).where(db.Job.id == job.id)
            status = None
            for _ in range(100):  # 5 s at most
                status = await session.scalar(status_query)
                if status not in (JobStatus.QUEUED, JobStatus.RUNNING):
                    break
                await asyncio.sleep(0.05)
            running.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await running
        await engine.dispose()
        return status

    # No handler for reindexAll yet, so it fails, but it ran.
    assert asyncio.run(scenario()) == JobStatus.FAILED


def test_the_heartbeat_tells_whether_the_worker_is_alive(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    beat = tmp_path / "heartbeat"
    monkeypatch.setattr(worker_module, "HEARTBEAT_FILE", beat)
    assert not worker_module.is_alive()

    async def beat_once() -> None:
        beating = asyncio.create_task(worker_module.heartbeat())
        await asyncio.sleep(0.1)
        beating.cancel()

    asyncio.run(beat_once())
    assert worker_module.is_alive()

    stale = time.time() - worker_module.HEARTBEAT_MAX_AGE_SECONDS - 1
    os.utime(beat, (stale, stale))
    assert not worker_module.is_alive()
