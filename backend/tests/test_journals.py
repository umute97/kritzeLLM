import asyncio
import hashlib

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from kritzellm.db import models as db
from kritzellm.ids import Prefix, new_id

pytestmark = pytest.mark.db


def _create(client: TestClient, name: str, **fields: object) -> dict:
    response = client.post("/journals", json={"name": name, **fields})
    assert response.status_code == 201, response.text
    return response.json()


def test_create_and_get(db_client: TestClient) -> None:
    response = db_client.post(
        "/journals", json={"name": "Summer 2026", "description": "Lisbon & Porto"}
    )
    assert response.status_code == 201
    journal = response.json()
    assert journal["id"].startswith("jrn_")
    assert response.headers["location"] == f"/api/v1/journals/{journal['id']}"
    assert journal["name"] == "Summer 2026"
    assert journal["description"] == "Lisbon & Porto"
    assert journal["pageCount"] == 0
    assert journal["createdAt"] == journal["updatedAt"]

    assert db_client.get(f"/journals/{journal['id']}").json() == journal


def test_unknown_journal_is_404(db_client: TestClient) -> None:
    for method in ("GET", "PATCH", "DELETE"):
        response = db_client.request(
            method, f"/journals/{new_id(Prefix.JOURNAL)}", json={} if method == "PATCH" else None
        )
        assert response.status_code == 404
        assert response.headers["content-type"] == "application/problem+json"
        assert response.json()["detail"] == "Journal not found."


def test_update_changes_only_the_given_fields(db_client: TestClient) -> None:
    journal = _create(db_client, "Summer", description="Holidays")

    renamed = db_client.patch(f"/journals/{journal['id']}", json={"name": "Summer 2026 🌻"}).json()
    assert renamed["name"] == "Summer 2026 🌻"
    assert renamed["description"] == "Holidays"
    assert renamed["updatedAt"] > journal["updatedAt"]

    cleared = db_client.patch(f"/journals/{journal['id']}", json={"description": None}).json()
    assert cleared["name"] == "Summer 2026 🌻"
    assert cleared["description"] is None

    unchanged = db_client.patch(f"/journals/{journal['id']}", json={}).json()
    assert unchanged == cleared


def test_name_cannot_be_null(db_client: TestClient) -> None:
    journal = _create(db_client, "Named")
    response = db_client.patch(f"/journals/{journal['id']}", json={"name": None})
    assert response.status_code == 422
    assert [error["pointer"] for error in response.json()["errors"]] == ["/name"]


def test_delete(db_client: TestClient) -> None:
    journal = _create(db_client, "Short-lived")
    response = db_client.delete(f"/journals/{journal['id']}")
    assert response.status_code == 204
    assert response.content == b""
    assert db_client.get(f"/journals/{journal['id']}").status_code == 404


def _all_ids(client: TestClient, limit: int) -> list[list[str]]:
    pages, cursor = [], None
    while True:
        params = {"limit": limit} | ({"cursor": cursor} if cursor else {})
        body = client.get("/journals", params=params).json()
        pages.append([journal["id"] for journal in body["items"]])
        cursor = body["nextCursor"]
        if cursor is None:
            return pages


def test_list_is_newest_first_and_paginates(db_client: TestClient) -> None:
    created = [_create(db_client, f"Volume {n}")["id"] for n in range(5)]
    newest_first = sorted(created, reverse=True)

    pages = _all_ids(db_client, limit=2)
    listed = [journal_id for page in pages for journal_id in page]
    assert [journal_id for journal_id in listed if journal_id in created] == newest_first
    assert len(listed) == len(set(listed))
    assert all(len(page) <= 2 for page in pages)


def test_cursor_of_a_deleted_journal_still_works(db_client: TestClient) -> None:
    older, middle, newer = (_create(db_client, f"Cursor {n}")["id"] for n in range(3))
    db_client.delete(f"/journals/{middle}")

    body = db_client.get("/journals", params={"cursor": middle, "limit": 100}).json()
    ids = [journal["id"] for journal in body["items"]]
    assert older in ids
    assert newer not in ids


def test_malformed_cursor_is_422(db_client: TestClient) -> None:
    response = db_client.get("/journals", params={"cursor": new_id(Prefix.PAGE)})
    assert response.status_code == 422
    assert [error["parameter"] for error in response.json()["errors"]] == ["cursor"]


async def _add_pages(database_url: str, journal_id: str, count: int) -> None:
    engine = create_async_engine(database_url)
    async with AsyncSession(engine) as session:
        session.add_all(
            db.Page(
                journal_id=journal_id,
                page_number=number,
                original_filename=f"{number}.jpg",
                original_media_type="image/jpeg",
                sha256=hashlib.sha256(f"{journal_id} {number}".encode()).digest(),
                width=100,
                height=100,
            )
            for number in range(1, count + 1)
        )
        await session.commit()
    await engine.dispose()


def test_page_count(db_client: TestClient, database_url: str) -> None:
    journal = _create(db_client, "With pages")
    asyncio.run(_add_pages(database_url, journal["id"], 3))

    assert db_client.get(f"/journals/{journal['id']}").json()["pageCount"] == 3
    listed = db_client.get("/journals", params={"limit": 100}).json()["items"]
    assert next(j for j in listed if j["id"] == journal["id"])["pageCount"] == 3
