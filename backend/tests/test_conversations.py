import asyncio
from datetime import UTC, datetime

import pytest
from conftest import ok, run_sql
from fastapi.testclient import TestClient
from pydantic import PostgresDsn
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from kritzellm.api.schemas.conversations import MAX_QUESTIONS, MessageRole
from kritzellm.config import Settings
from kritzellm.core.conversations import ChatFullError, add_message
from kritzellm.db import models as db
from kritzellm.ids import Prefix, new_id
from kritzellm.main import create_app

pytestmark = pytest.mark.db


def _create(client: TestClient, **fields: object) -> dict:
    response = client.post("/conversations", json=fields)
    assert response.status_code == 201, response.text
    return response.json()


def _say(database_url: str, conversation_id: str, *messages: tuple[MessageRole, str]) -> None:
    """Stores messages the way the chat will, each in its own transaction."""

    async def store() -> None:
        engine = create_async_engine(database_url)
        async with AsyncSession(engine) as session:
            for role, content in messages:
                await add_message(session, conversation_id, role, content)
                await session.commit()
        await engine.dispose()

    asyncio.run(store())


def _listed(client: TestClient, limit: int = 100) -> list[list[str]]:
    pages, cursor = [], None
    while True:
        params = {"limit": limit} | ({"cursor": cursor} if cursor else {})
        body = ok(client.get("/conversations", params=params))
        pages.append([conversation["id"] for conversation in body["items"]])
        cursor = body["nextCursor"]
        if cursor is None:
            return pages


def _order(client: TestClient, ids: list[str], limit: int = 100) -> list[str]:
    """`ids` in the order the list shows them."""
    return [found for page in _listed(client, limit) for found in page if found in ids]


def test_create_and_get(db_client: TestClient) -> None:
    response = db_client.post("/conversations", json={"title": "Sweet peas 🌱"})
    assert response.status_code == 201
    conversation = response.json()
    assert conversation["id"].startswith("cnv_")
    assert response.headers["location"] == f"/api/v1/conversations/{conversation['id']}"
    assert conversation["title"] == "Sweet peas 🌱"
    assert conversation["createdAt"] == conversation["updatedAt"]

    assert ok(db_client.get(f"/conversations/{conversation['id']}")) == conversation | {
        "messages": []
    }


def test_title_is_optional_and_can_change(db_client: TestClient) -> None:
    conversation = _create(db_client)
    assert conversation["title"] is None
    url = f"/conversations/{conversation['id']}"

    renamed = ok(db_client.patch(url, json={"title": "Grandma's recipes"}))
    assert renamed["title"] == "Grandma's recipes"
    assert renamed["updatedAt"] > conversation["updatedAt"]
    assert ok(db_client.patch(url, json={})) == renamed
    assert ok(db_client.patch(url, json={"title": None}))["title"] is None

    for title in ("", "x" * 201):
        response = db_client.patch(url, json={"title": title})
        assert response.status_code == 422
        assert [error["pointer"] for error in response.json()["errors"]] == ["/title"]


def test_unknown_conversation_is_404(db_client: TestClient) -> None:
    for method in ("GET", "PATCH", "DELETE"):
        response = db_client.request(
            method,
            f"/conversations/{new_id(Prefix.CONVERSATION)}",
            json={} if method == "PATCH" else None,
        )
        assert response.status_code == 404
        assert response.json()["detail"] == "Conversation not found."


def test_messages_come_back_oldest_first(db_client: TestClient, database_url: str) -> None:
    conversation = _create(db_client)
    _say(
        database_url,
        conversation["id"],
        (MessageRole.USER, "When did I plant the sweet peas?"),
        (MessageRole.ASSISTANT, "On Saturday, March 3, by the fence."),
        (MessageRole.USER, "And the basil?"),
    )

    messages = ok(db_client.get(f"/conversations/{conversation['id']}"))["messages"]
    assert [(m["role"], m["content"]) for m in messages] == [
        ("user", "When did I plant the sweet peas?"),
        ("assistant", "On Saturday, March 3, by the fence."),
        ("user", "And the basil?"),
    ]
    assert all(m["id"].startswith("msg_") for m in messages)


def test_list_is_most_recently_active_first(db_client: TestClient, database_url: str) -> None:
    older, newer = _create(db_client)["id"], _create(db_client)["id"]
    assert _order(db_client, [older, newer]) == [newer, older]

    _say(database_url, older, (MessageRole.USER, "Still there?"))
    assert _order(db_client, [older, newer]) == [older, newer]
    detail = ok(db_client.get(f"/conversations/{older}"))
    assert detail["updatedAt"] > detail["createdAt"]


def test_paging_goes_through_every_conversation_once(
    db_client: TestClient, database_url: str
) -> None:
    created = [_create(db_client)["id"] for _ in range(5)]
    # The same activity for all, so the order falls back to the ID.
    run_sql(
        database_url,
        update(db.Conversation)
        .where(db.Conversation.id.in_(created))
        .values(updated_at=datetime(2001, 1, 1, tzinfo=UTC)),
    )

    pages = _listed(db_client, limit=2)
    listed = [found for page in pages for found in page]
    assert [found for found in listed if found in created] == sorted(created, reverse=True)
    assert len(listed) == len(set(listed))
    assert all(len(page) <= 2 for page in pages)


def test_malformed_cursor_is_422(db_client: TestClient) -> None:
    for cursor in (new_id(Prefix.CONVERSATION), f"{new_id(Prefix.JOURNAL)}.1", "cnv_.1"):
        response = db_client.get("/conversations", params={"cursor": cursor})
        assert response.status_code == 422, cursor
        assert [error["parameter"] for error in response.json()["errors"]] == ["cursor"]


def test_delete_takes_the_messages_along(db_client: TestClient, database_url: str) -> None:
    conversation = _create(db_client)
    _say(database_url, conversation["id"], (MessageRole.USER, "Forget this."))

    response = db_client.delete(f"/conversations/{conversation['id']}")
    assert response.status_code == 204
    assert db_client.get(f"/conversations/{conversation['id']}").status_code == 404

    async def count() -> int | None:
        engine = create_async_engine(database_url)
        async with AsyncSession(engine) as session:
            left = await session.scalar(
                select(func.count()).where(db.Message.conversation_id == conversation["id"])
            )
        await engine.dispose()
        return left

    assert asyncio.run(count()) == 0


def test_a_chat_takes_a_limited_number_of_questions(
    db_client: TestClient, database_url: str
) -> None:
    conversation = _create(db_client)
    turns = [(MessageRole.USER, f"Question {n}") for n in range(MAX_QUESTIONS)]
    _say(database_url, conversation["id"], *turns)
    # The last question still gets its answer.
    _say(database_url, conversation["id"], (MessageRole.ASSISTANT, "Answer"))

    with pytest.raises(ChatFullError, match=f"already has {MAX_QUESTIONS} questions"):
        _say(database_url, conversation["id"], (MessageRole.USER, "One more?"))
    assert len(ok(db_client.get(f"/conversations/{conversation['id']}"))["messages"]) == (
        MAX_QUESTIONS + 1
    )


def test_conversations_are_still_there_after_a_restart(
    db_client: TestClient, database_url: str
) -> None:
    conversation = _create(db_client, title="Dreams about the sea")
    _say(database_url, conversation["id"], (MessageRole.USER, "What did I dream in October?"))
    before = ok(db_client.get(f"/conversations/{conversation['id']}"))

    settings = Settings(api_token=None, database_url=PostgresDsn(database_url))
    with TestClient(create_app(settings), base_url="http://test/api/v1") as restarted:
        assert ok(restarted.get(f"/conversations/{conversation['id']}")) == before
