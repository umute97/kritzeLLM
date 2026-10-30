from collections.abc import Callable

import pytest
from conftest import chunks_of, get_job, get_page, new_journal, ok, run_sql, upload
from fastapi.testclient import TestClient
from sqlalchemy import update

from kritzellm.config import Settings
from kritzellm.core import indexing
from kritzellm.db import models as db

pytestmark = pytest.mark.db

MakeImage = Callable[..., bytes]


def test_reindex_queues_one_job_for_the_library(db_client: TestClient) -> None:
    response = db_client.post("/admin/reindex")

    job = ok(response, 202)
    assert response.headers["location"] == f"/api/v1/jobs/{job['id']}"
    assert (job["kind"], job["status"], job["target"]) == ("reindexAll", "queued", None)
    assert ok(db_client.post("/admin/reindex"), 202)["id"] == job["id"]


def test_reindex_embeds_every_ready_page_again(
    db_client: TestClient,
    make_image: MakeImage,
    settings: Settings,
    work: Callable[[], None],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    url = str(settings.database_url)
    journal_id = new_journal(db_client)
    (ready,) = upload(db_client, journal_id, make_image(color="gold"))
    work()
    run_sql(
        url,
        update(db.Chunk).where(db.Chunk.page_id == ready["page"]["id"]).values(embed_model="old"),
    )
    with monkeypatch.context() as patch:

        async def no_vectors(texts: list[str], settings: Settings) -> list[list[float]]:
            raise RuntimeError("OpenAI is down")

        patch.setattr(indexing, "embed", no_vectors)
        (failed,) = upload(db_client, journal_id, make_image(color="silver"))
        work()

    job = ok(db_client.post("/admin/reindex"), 202)
    work()

    job = get_job(db_client, job["id"])
    assert job["status"] == "succeeded"
    assert job["progress"]["done"] == job["progress"]["total"] >= 1
    chunks = chunks_of(url, ready["page"]["id"])
    assert chunks
    assert {chunk.embed_model for chunk in chunks} == {"test"}
    assert get_page(db_client, ready["page"]["id"])["status"] == "ready"
    assert get_page(db_client, failed["page"]["id"])["status"] == "failed"
    assert chunks_of(url, failed["page"]["id"]) == []
