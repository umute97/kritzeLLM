import logging
from collections.abc import AsyncGenerator, AsyncIterator
from contextlib import aclosing

from fastapi import APIRouter, Request, Response, status
from fastapi.sse import EventSourceResponse, format_sse_event

from kritzellm.core import conversations as core
from kritzellm.core.agent import answer
from kritzellm.core.rows import add_new, update_existing
from kritzellm.db import models as db

from ..deps import AppSettings, Session
from ..errors import problem_for, problem_responses
from ..schemas.conversations import (
    Conversation,
    ConversationCreate,
    ConversationDetail,
    ConversationList,
    ConversationUpdate,
    ErrorEvent,
    Message,
    MessageEndEvent,
    Question,
    StreamEvent,
)
from .params import ConversationCursor, ConversationIdPath, Limit, location_header, set_location

logger = logging.getLogger(__name__)

router = APIRouter(tags=["conversations"], responses=problem_responses(400, 401, 422))


@router.get(
    "/conversations",
    summary="List conversations",
)
async def list_conversations(
    session: Session, limit: Limit = 25, cursor: ConversationCursor = None
) -> ConversationList:
    """Lists all conversations, the most recently active first."""
    conversations, next_cursor = await core.list_conversations(session, limit=limit, cursor=cursor)
    return ConversationList(
        items=[Conversation.model_validate(conversation) for conversation in conversations],
        next_cursor=next_cursor,
    )


@router.post(
    "/conversations",
    status_code=status.HTTP_201_CREATED,
    summary="Start a conversation",
    responses={
        201: {"headers": location_header("URL of the new conversation.")},
    },
)
async def create_conversation(
    body: ConversationCreate, session: Session, request: Request, response: Response
) -> Conversation:
    """Starts an empty conversation to ask the journal things in."""
    conversation = await add_new(session, db.Conversation(title=body.title))
    await session.commit()
    set_location(request, response, "get_conversation", conversationId=conversation.id)
    return Conversation.model_validate(conversation)


@router.get(
    "/conversations/{conversationId}",
    summary="Get a conversation",
    responses=problem_responses(404),
)
async def get_conversation(
    conversation_id: ConversationIdPath, session: Session
) -> ConversationDetail:
    """Returns a conversation with all of its messages, oldest first.

    A conversation takes up to 20 questions, so it holds at most 40 messages.
    """
    return ConversationDetail.model_validate(await core.get_conversation(session, conversation_id))


@router.patch(
    "/conversations/{conversationId}",
    summary="Update a conversation",
    responses=problem_responses(404),
)
async def update_conversation(
    conversation_id: ConversationIdPath, body: ConversationUpdate, session: Session
) -> Conversation:
    """Renames a conversation. Only the given fields change."""
    changes = body.model_dump(exclude_unset=True, by_alias=False)
    conversation = await update_existing(session, db.Conversation, conversation_id, changes)
    await session.commit()
    return Conversation.model_validate(conversation)


@router.delete(
    "/conversations/{conversationId}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    summary="Delete a conversation",
    responses=problem_responses(404),
)
async def delete_conversation(conversation_id: ConversationIdPath, session: Session) -> None:
    """Deletes a conversation with all of its messages.

    This can't be undone.
    """
    await core.delete_conversation(session, conversation_id)
    await session.commit()


async def _stream(events: AsyncGenerator[StreamEvent], instance: str) -> AsyncIterator[bytes]:
    async with aclosing(events):
        try:
            async for event in events:
                yield format_sse_event(data_str=event.model_dump_json(), event=event.type)
        except Exception as exc:
            if problem_for(exc).status == 500:
                logger.exception("An answer failed")
            failed = ErrorEvent(problem=problem_for(exc, instance))
            yield format_sse_event(data_str=failed.model_dump_json(), event=failed.type)


async def _saved_answer(events: AsyncGenerator[StreamEvent]) -> Message:
    async with aclosing(events):
        async for event in events:
            if isinstance(event, MessageEndEvent):
                return event.message
    raise RuntimeError("The answer ended without its message")


@router.post(
    "/conversations/{conversationId}/messages",
    summary="Ask a question",
    response_model=Message,
    responses={
        200: {
            "description": (
                "The saved answer, or with `Accept: text/event-stream` the answer as it's written: "
                "server-sent events, each a `ChatStreamEvent`."
            ),
            "content": {
                "text/event-stream": {"schema": {"$ref": "#/components/schemas/ChatStreamEvent"}}
            },
        },
        **problem_responses(404, 409, 502),
    },
)
async def ask_question(
    conversation_id: ConversationIdPath,
    body: Question,
    session: Session,
    settings: AppSettings,
    request: Request,
) -> Response | Message:
    """Asks the journal a question and answers it, citing the blocks the answer rests on.

    The helper searches and reads the journal first, then answers with `[n]` citations, one for
    each of the answer's `sources`. It only cites blocks it actually read. The question and its
    answer are saved together once the answer is done; if it fails or the stream is closed early,
    nothing is saved.

    With `Accept: text/event-stream` the answer streams as it's written, ending with `messageEnd`
    (the same `Message` JSON mode returns) or `error`. A conversation takes up to 20 questions;
    after that, this is a `409`. A `502` means the chat model failed.
    """
    await core.check_room(session, conversation_id)
    await session.close()
    events = answer(request.app.state.sessionmaker, settings, conversation_id, body.content)
    if "text/event-stream" in request.headers.get("accept", ""):
        return EventSourceResponse(_stream(events, request.url.path))
    return await _saved_answer(events)
