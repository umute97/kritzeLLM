import asyncio
import contextlib
import os
import time
from collections.abc import Callable
from pathlib import Path

import pytest
from conftest import FakeVisionModel, get_job, get_page, new_journal, upload
from fastapi.testclient import TestClient
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


PAGE = {
    "page_label": "7",
    "entry_dates": ["2026-03-15", "2026-03-14", "2026-03-15"],
    "blocks": [
        {"kind": "heading", "text": "14. März", "uncertain": False},
        {"kind": "paragraph", "text": "Endlich beim Arzt gewesen.", "uncertain": False},
        {"kind": "marginNote", "text": "anrufen [?]", "uncertain": True},
    ],
}


def test_upload_queues_an_ingest_job_per_new_page(
    db_client: TestClient, make_image: MakeImage
) -> None:
    items = upload(db_client, new_journal(db_client), make_image(color="red"))

    job = items[0]["job"]
    assert job["id"].startswith("job_")
    assert job["kind"] == "ingestPage"
    assert job["status"] == "queued"
    assert job["target"] == {"type": "page", "id": items[0]["page"]["id"]}
    assert (job["progress"], job["error"]) == (None, None)
    assert (job["startedAt"], job["finishedAt"]) == (None, None)
    assert get_job(db_client, job["id"]) == job


def test_a_duplicate_gets_the_pages_latest_job(
    db_client: TestClient, make_image: MakeImage
) -> None:
    journal_id = new_journal(db_client)
    photo = make_image(color="blue")
    first = upload(db_client, journal_id, photo)[0]

    again, twice = upload(db_client, journal_id, photo, photo)

    assert again["duplicate"]
    assert twice["duplicate"]
    assert again["job"]["id"] == twice["job"]["id"] == first["job"]["id"]


def test_the_worker_transcribes_the_page(
    db_client: TestClient,
    make_image: MakeImage,
    work: Callable[[], None],
    vision_model: FakeVisionModel,
) -> None:
    vision_model.outputs = [PAGE]
    (item,) = upload(db_client, new_journal(db_client), make_image(color="green"))

    work()

    job = get_job(db_client, item["job"]["id"])
    assert job["status"] == "succeeded"
    assert job["progress"] == {"done": 2, "total": 2}
    assert job["error"] is None
    assert job["createdAt"] <= job["startedAt"] <= job["finishedAt"]
    page = get_page(db_client, item["page"]["id"])
    assert (page["status"], page["error"]) == ("ready", None)
    assert page["transcriptionModel"] == "test"
    assert page["pageLabel"] == "7"
    assert page["entryDates"] == ["2026-03-14", "2026-03-15"]
    blocks = [(b["seq"], b["kind"], b["text"], b["uncertain"]) for b in page["blocks"]]
    assert blocks == [
        (0, "heading", "14. März", False),
        (1, "paragraph", "Endlich beim Arzt gewesen.", False),
        (2, "marginNote", "anrufen [?]", True),
    ]
    assert all(b["id"].startswith("blk_") and b["pageId"] == page["id"] for b in page["blocks"])
    assert len(vision_model.calls) == 1


def test_the_fake_model_needs_no_key(
    db_client: TestClient, make_image: MakeImage, work: Callable[[], None]
) -> None:
    (item,) = upload(db_client, new_journal(db_client), make_image(color="lime"))

    work()

    page = get_page(db_client, item["page"]["id"])
    assert page["status"] == "ready"
    assert page["blocks"]


def test_label_and_dates_set_by_hand_are_kept(
    db_client: TestClient,
    make_image: MakeImage,
    work: Callable[[], None],
    vision_model: FakeVisionModel,
) -> None:
    vision_model.outputs = [PAGE]
    (item,) = upload(db_client, new_journal(db_client), make_image(color="pink"))
    page_id = item["page"]["id"]
    fixed = {"pageLabel": "VII", "entryDates": ["2026-01-01"]}
    assert db_client.patch(f"/pages/{page_id}", json=fixed).status_code == 200

    work()

    page = get_page(db_client, page_id)
    assert (page["pageLabel"], page["entryDates"]) == ("VII", ["2026-01-01"])
    assert len(page["blocks"]) == 3


def test_transcribing_again_replaces_the_blocks(
    db_client: TestClient,
    make_image: MakeImage,
    settings: Settings,
    work: Callable[[], None],
    vision_model: FakeVisionModel,
) -> None:
    vision_model.outputs = [PAGE]
    (item,) = upload(db_client, new_journal(db_client), make_image(color="cyan"))
    work()

    async def queue_again() -> None:
        engine = create_async_engine(str(settings.database_url))
        async with engine.begin() as connection:
            await connection.execute(
                update(db.Job).where(db.Job.id == item["job"]["id"]).values(status=JobStatus.QUEUED)
            )
        await engine.dispose()

    asyncio.run(queue_again())
    vision_model.outputs = [
        {**PAGE, "blocks": [{"kind": "other", "text": "Neu", "uncertain": False}]}
    ]
    work()

    page = get_page(db_client, item["page"]["id"])
    assert [(b["seq"], b["text"]) for b in page["blocks"]] == [(0, "Neu")]


def test_a_model_that_keeps_answering_nonsense_fails_the_page(
    db_client: TestClient,
    make_image: MakeImage,
    work: Callable[[], None],
    vision_model: FakeVisionModel,
) -> None:
    vision_model.outputs = [{**PAGE, "entry_dates": ["someday"]}]
    (item,) = upload(db_client, new_journal(db_client), make_image(color="brown"))

    work()

    job = get_job(db_client, item["job"]["id"])
    assert job["status"] == "failed"
    assert len(vision_model.calls) == 2
    page = get_page(db_client, item["page"]["id"])
    assert (page["status"], page["error"]) == ("failed", job["error"])
    assert page["blocks"] == []


def test_a_failing_job_fails_its_page(
    db_client: TestClient,
    make_image: MakeImage,
    work: Callable[[], None],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def boom(session: AsyncSession, job: db.Job, settings: Settings) -> None:
        raise RuntimeError("The pen ran out of ink")

    monkeypatch.setitem(worker_module.HANDLERS, JobKind.INGEST_PAGE, boom)
    (item,) = upload(db_client, new_journal(db_client), make_image(color="purple"))

    work()

    job = get_job(db_client, item["job"]["id"])
    assert job["status"] == "failed"
    assert job["finishedAt"] is not None
    error = job["error"]
    assert (error["title"], error["status"]) == ("Job failed", 500)
    assert error["detail"] == "The pen ran out of ink"
    page = get_page(db_client, item["page"]["id"])
    assert (page["status"], page["error"]) == ("failed", job["error"])


def test_every_job_kind_has_a_handler() -> None:
    assert worker_module.HANDLERS.keys() == set(JobKind)


def test_interrupted_jobs_run_again(
    db_client: TestClient, make_image: MakeImage, settings: Settings, work: Callable[[], None]
) -> None:
    (item,) = upload(db_client, new_journal(db_client), make_image(color="orange"))
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
    assert get_job(db_client, job_id)["status"] == "running"

    work()

    assert get_job(db_client, job_id)["status"] == "succeeded"


def test_deleting_a_page_deletes_its_jobs(
    db_client: TestClient, make_image: MakeImage, work: Callable[[], None]
) -> None:
    (item,) = upload(db_client, new_journal(db_client), make_image(color="yellow"))

    assert db_client.delete(f"/pages/{item['page']['id']}").status_code == 204
    assert db_client.get(f"/jobs/{item['job']['id']}").status_code == 404
    work()  # Nothing left to trip over.


def test_a_failed_upload_leaves_no_pages_files_or_jobs(
    db_client: TestClient,
    make_image: MakeImage,
    data_dir: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    journal_id = new_journal(db_client)
    publish = Staging.publish
    calls = []

    def flaky_publish(self: Staging, staged: Path, page_id: str) -> None:
        calls.append(page_id)
        if len(calls) == 2:
            raise OSError("Disk full")
        publish(self, staged, page_id)

    monkeypatch.setattr(Staging, "publish", flaky_publish)
    with pytest.raises(OSError, match="Disk full"):
        upload(db_client, journal_id, make_image(color="red"), make_image(color="blue"))

    assert db_client.get(f"/pages?journalId={journal_id}").json()["items"] == []
    assert not (data_dir / "pages").exists() or not any((data_dir / "pages").iterdir())
    listed = {job["target"]["id"] for job in db_client.get("/jobs?limit=100").json()["items"]}
    assert listed.isdisjoint(calls)


def test_list_is_newest_first_and_pages(db_client: TestClient, make_image: MakeImage) -> None:
    items = upload(
        db_client,
        new_journal(db_client),
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
    (done,) = upload(db_client, new_journal(db_client), make_image(color=(1, 2, 3)))
    work()
    (queued,) = upload(db_client, new_journal(db_client), make_image(color=(3, 2, 1)))

    def ids(**params: str) -> set[str]:
        response = db_client.get("/jobs", params={"limit": "100", **params})
        assert response.status_code == 200, response.text
        return {job["id"] for job in response.json()["items"]}

    assert queued["job"]["id"] in ids(status="queued")
    assert done["job"]["id"] not in ids(status="queued")
    assert done["job"]["id"] in ids(status="succeeded", kind="ingestPage")
    assert done["job"]["id"] not in ids(kind="reindexPage")


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
            contextlib.aclosing(Worker(settings)) as worker,
            AsyncSession(engine, expire_on_commit=False) as session,
        ):
            page = db.Page(
                journal=db.Journal(name="Wake up"),
                page_number=1,
                original_filename="a.jpg",
                original_media_type="image/jpeg",
                sha256=os.urandom(32),
                width=1,
                height=1,
            )
            session.add(page)
            await session.commit()
            running = asyncio.create_task(worker.run())
            await asyncio.sleep(0.5)  # Let it catch up and go to sleep.
            job = await jobs.enqueue(session, JobKind.REINDEX_PAGE, page_id=page.id)
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

    assert asyncio.run(scenario()) == JobStatus.SUCCEEDED


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
