import asyncio
import itertools
import json
import uuid
from collections.abc import Callable
from typing import Any

import pytest
from conftest import FakeVisionModel, ScriptedChatModel, new_journal, ok, upload
from fastapi.testclient import TestClient
from pydantic import PostgresDsn
from pydantic_ai.exceptions import ModelHTTPError, UserError
from pydantic_ai.messages import (
    ModelRequest,
    ModelResponse,
    TextPart,
    ToolReturnPart,
    UserPromptPart,
)
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from kritzellm.config import Settings
from kritzellm.core import llm
from kritzellm.core.agent import title_from
from kritzellm.core.conversations import add_message
from kritzellm.domain import MAX_QUESTIONS, MessageRole
from kritzellm.ids import Prefix, new_id
from kritzellm.main import create_app

pytestmark = pytest.mark.db

MakeImage = Callable[..., bytes]
_sizes = itertools.count()


def word() -> str:
    """A word no other page has, so searches only find this test's pages."""
    return f"wort{uuid.uuid4().hex[:10]}"


@pytest.fixture
def add_page(
    db_client: TestClient, make_image: MakeImage, vision_model: FakeVisionModel, work: Any
) -> Callable[..., dict]:
    """Uploads a page that reads as `texts`, one block each, indexes it, and returns it."""

    def add(journal_id: str, *texts: str, dates: tuple[str, ...] = ()) -> dict:
        blocks = [{"kind": "paragraph", "text": text, "uncertain": False} for text in texts]
        vision_model.outputs = [{"page_label": None, "entry_dates": list(dates), "blocks": blocks}]
        (item,) = upload(db_client, journal_id, make_image(size=(200 + next(_sizes), 80)))
        work()
        return ok(db_client.get(f"/pages/{item['page']['id']}"))

    return add


def new_conversation(client: TestClient) -> str:
    return ok(client.post("/conversations", json={}), 201)["id"]


def ask(client: TestClient, conversation_id: str, question: str) -> Any:
    return client.post(f"/conversations/{conversation_id}/messages", json={"content": question})


def ask_streaming(client: TestClient, conversation_id: str, question: str) -> list[dict]:
    """The events of a streamed answer, each its `data` with the `event` name checked."""
    response = client.post(
        f"/conversations/{conversation_id}/messages",
        json={"content": question},
        headers={"Accept": "text/event-stream"},
    )
    assert response.status_code == 200, response.text
    assert response.headers["content-type"].startswith("text/event-stream")
    events = []
    for frame in response.text.strip().split("\n\n"):
        fields = dict(line.split(": ", 1) for line in frame.splitlines())
        data = json.loads(fields["data"])
        assert fields["event"] == data["type"]
        events.append(data)
    return events


def tool_returns(request: list) -> list[str]:
    return [
        str(part.content)
        for message in request
        if isinstance(message, ModelRequest)
        for part in message.parts
        if isinstance(part, ToolReturnPart)
    ]


def test_answers_cite_only_blocks_they_read(
    db_client: TestClient, add_page: Callable[..., dict], chat_model: ScriptedChatModel
) -> None:
    rare = word()
    journal = new_journal(db_client, "Garden")
    page = add_page(
        journal, f"Planted the {rare} by the fence.", "Rain all day.", dates=("2026-03-03",)
    )
    conversation = new_conversation(db_client)
    chat_model.script = [
        {"name": "search_journal", "args": {"query": rare, "journal_id": journal}},
        "You planted them by the fence [1], under a full moon [7].",
    ]

    message = ok(ask(db_client, conversation, f"Where did I plant the {rare}?"))

    assert message["role"] == "assistant"
    assert message["content"] == "You planted them by the fence [1], under a full moon."
    (block, _) = page["blocks"]
    assert message["sources"] == [
        {
            "ref": 1,
            "blockId": block["id"],
            "pageId": page["id"],
            "journalId": journal,
            "pageNumber": 1,
            "entryDates": ["2026-03-03"],
            "quote": f"Planted the {rare} by the fence.",
        }
    ]
    assert message["toolCalls"] == [
        {"name": "search_journal", "args": {"query": rare, "journal_id": journal}, "pages": 1}
    ]
    (found,) = tool_returns(chat_model.requests[1])
    assert "Page 1 of Garden (2026-03-03; id " in found
    assert f"[1] Planted the {rare} by the fence." in found

    saved = ok(db_client.get(f"/conversations/{conversation}"))
    assert [m["role"] for m in saved["messages"]] == ["user", "assistant"]
    assert saved["messages"][0]["content"] == f"Where did I plant the {rare}?"
    assert saved["messages"][1] == message
    assert saved["title"] == f"Where did I plant the {rare}?"


def test_the_next_question_sees_the_thread_without_old_citations(
    db_client: TestClient, chat_model: ScriptedChatModel
) -> None:
    conversation = new_conversation(db_client)
    chat_model.script = ["Nothing about sweet peas [3].", "Still nothing, sorry."]
    ok(ask(db_client, conversation, "Sweet peas?"))
    ok(ask(db_client, conversation, "Are you sure?"))

    second = chat_model.requests[1]
    texts = [
        part.content
        for message in second
        for part in message.parts
        if isinstance(part, UserPromptPart | TextPart)
    ]
    assert texts == ["Sweet peas?", "Nothing about sweet peas.", "Are you sure?"]
    assert isinstance(second[1], ModelResponse)
    assert ok(db_client.get(f"/conversations/{conversation}"))["title"] == "Sweet peas?"


def test_streaming_and_json_end_with_the_same_message(
    db_client: TestClient, add_page: Callable[..., dict], chat_model: ScriptedChatModel
) -> None:
    rare = word()
    journal = new_journal(db_client)
    add_page(journal, f"The {rare} came back.")
    script = [
        {"name": "find_exact", "args": {"text": rare}},
        f"The {rare} came back [1].",
    ]

    chat_model.script = list(script)
    in_json = ok(ask(db_client, new_conversation(db_client), "Did it come back?"))
    chat_model.script = list(script)
    events = ask_streaming(db_client, new_conversation(db_client), "Did it come back?")

    assert [event["type"] for event in events[:3]] == ["messageStart", "toolCall", "toolResult"]
    assert events[1]["name"] == events[2]["name"] == "find_exact"
    assert events[1]["id"] == events[2]["id"]
    assert events[2]["pages"] == 1
    deltas = [event["text"] for event in events if event["type"] == "textDelta"]
    assert len(deltas) > 1
    assert "".join(deltas) == f"The {rare} came back [1]."
    assert [event["type"] for event in events[-2:]] == ["source", "messageEnd"]
    streamed = events[-1]["message"]
    assert events[-2]["source"] == streamed["sources"][0]

    def comparable(message: dict) -> dict:
        return {key: value for key, value in message.items() if key not in ("id", "createdAt")}

    assert comparable(streamed) == comparable(in_json)


def test_a_full_chat_is_409_before_the_model_is_asked(
    db_client: TestClient, database_url: str, chat_model: ScriptedChatModel
) -> None:
    conversation = new_conversation(db_client)

    async def fill() -> None:
        engine = create_async_engine(database_url)
        async with AsyncSession(engine) as session:
            for n in range(MAX_QUESTIONS):
                await add_message(session, conversation, MessageRole.USER, f"Question {n}")
            await session.commit()
        await engine.dispose()

    asyncio.run(fill())

    for headers in ({}, {"Accept": "text/event-stream"}):
        response = db_client.post(
            f"/conversations/{conversation}/messages",
            json={"content": "One more?"},
            headers=headers,
        )
        assert response.status_code == 409
        assert "Start a new one" in response.json()["detail"]
    assert chat_model.requests == []


def test_a_failed_answer_saves_nothing(
    db_client: TestClient, chat_model: ScriptedChatModel
) -> None:
    conversation = new_conversation(db_client)
    overloaded = ModelHTTPError(503, "gpt-6-luna", body="overloaded")

    chat_model.script = [overloaded]
    response = ask(db_client, conversation, "Hello?")
    assert response.status_code == 502
    assert response.json()["detail"] == "The chat model couldn't answer. Try again later."
    assert "overloaded" not in response.text

    chat_model.script = [overloaded]
    events = ask_streaming(db_client, conversation, "Hello?")
    assert [event["type"] for event in events] == ["messageStart", "error"]
    assert events[-1]["problem"]["status"] == 502

    saved = ok(db_client.get(f"/conversations/{conversation}"))
    assert saved["messages"] == []
    assert saved["title"] is None


def test_an_answer_may_only_take_so_many_steps(
    db_client: TestClient, chat_model: ScriptedChatModel
) -> None:
    conversation = new_conversation(db_client)
    chat_model.script = [{"name": "list_pages", "args": {}}] * 10

    response = ask(db_client, conversation, "Read everything, please.")

    assert response.status_code == 502
    assert "too many steps" in response.json()["detail"]
    assert len(chat_model.requests) == 8


def test_the_tools_read_pages_and_keep_numbers(
    db_client: TestClient, add_page: Callable[..., dict], chat_model: ScriptedChatModel
) -> None:
    rare = word()
    journal = new_journal(db_client, "Travel")
    page = add_page(journal, "Morning.", f"Saw a {rare}.", "Lunch.", "Train home.", "Bed.")
    chat_model.script = [
        {"name": "list_pages", "args": {"journal_id": journal}},
        {"name": "read_page", "args": {"page_id": page["id"]}},
        [
            {"name": "find_exact", "args": {"text": rare, "journal_id": journal}},
            {"name": "read_block", "args": {"ref": 5}},
        ],
        [
            {"name": "read_page", "args": {"page_id": new_id(Prefix.PAGE)}},
            {"name": "read_block", "args": {"ref": 99}},
            {"name": "search_journal", "args": {"query": rare, "journal_id": "jrn_nope"}},
        ],
        "Done [2][5].",
    ]

    message = ok(ask(db_client, new_conversation(db_client), "Tell me about the trip."))

    # Each round's results, from the request after it (the requests carry the whole run so far).
    (listed,), (read,), (exact, around), (no_page, no_block, no_journal) = (
        tool_returns(chat_model.requests[n])[-count:]
        for n, count in ((1, 1), (2, 1), (3, 2), (4, 3))
    )
    assert listed == f"Page 1 of Travel (no date; id {page['id']})"
    assert read.splitlines()[1:] == [
        "[1] Morning.",
        f"[2] Saw a {rare}.",
        "[3] Lunch.",
        "[4] Train home.",
        "[5] Bed.",
    ]
    assert f"[2] Saw a {rare}." in exact
    assert around.splitlines()[1:] == ["[3] Lunch.", "[4] Train home.", "[5] Bed."]
    assert no_page.startswith("There's no page with the id")
    assert no_block == "There's no block [99] to read around."
    assert no_journal.startswith("There's no journal with the id jrn_nope")

    assert message["content"] == "Done [2][5]."
    assert [source["ref"] for source in message["sources"]] == [2, 5]
    assert [call["pages"] for call in message["toolCalls"]] == [1, 1, 1, 1, 0, 0, 0]


def test_searching_falls_back_to_words_without_embeddings(
    db_client: TestClient,
    add_page: Callable[..., dict],
    chat_model: ScriptedChatModel,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    rare = word()
    add_page(new_journal(db_client), f"The {rare} bloomed.")

    def not_set_up(name: str, api_key: str | None) -> None:
        raise UserError("Set the `OPENAI_API_KEY` environment variable.")

    monkeypatch.setattr(llm, "_embedder", not_set_up)
    chat_model.script = [{"name": "search_journal", "args": {"query": rare}}, "It bloomed [1]."]

    message = ok(ask(db_client, new_conversation(db_client), "Did it bloom?"))

    (found,) = tool_returns(chat_model.requests[1])
    assert found.startswith("Searching by meaning isn't available right now")
    assert f"[1] The {rare} bloomed." in found
    assert message["content"] == "It bloomed [1]."


def test_question_must_say_something(db_client: TestClient) -> None:
    conversation = new_conversation(db_client)
    for content in ("", "   ", "x" * 4001):
        response = ask(db_client, conversation, content)
        assert response.status_code == 422
        assert [error["pointer"] for error in response.json()["errors"]] == ["/content"]
    assert ask(db_client, new_id(Prefix.CONVERSATION), "Hello?").status_code == 404


def test_a_missing_openai_key_is_502(database_url: str, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    settings = Settings(
        api_token=None, database_url=PostgresDsn(database_url), chat_model="gpt-6-luna"
    )
    with TestClient(create_app(settings), base_url="http://test/api/v1") as client:
        conversation = new_conversation(client)
        response = ask(client, conversation, "Hello?")
    assert response.status_code == 502
    assert response.json()["detail"] == "The chat model isn't set up on the server."


@pytest.mark.parametrize(
    ("question", "title"),
    [
        ("  Where did I   plant the sweet peas? ", "Where did I plant the sweet peas?"),
        (
            "What did I write about the long walk along the river in the rain last spring, "
            "with grandma?",
            "What did I write about the long walk along the river in the…",
        ),
        ("x" * 70, "x" * 60 + "…"),
    ],
)
def test_title_from_the_first_question(question: str, title: str) -> None:
    assert title_from(question) == title
