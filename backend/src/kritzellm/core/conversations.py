"""Conversations: chat threads with the journal, and the messages in them."""

from collections.abc import Sequence
from datetime import UTC, datetime, timedelta

from sqlalchemy import delete, func, select, tuple_, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from kritzellm.api.schemas.conversations import Source, ToolCall
from kritzellm.db import models as db
from kritzellm.domain import CONVERSATION_CURSOR, MAX_QUESTIONS, MessageRole

from .errors import ConflictError, NotFoundError
from .pagination import join_cursor, paginate, split_cursor
from .rows import get_existing

_EPOCH = datetime(1970, 1, 1, tzinfo=UTC)
_MICROSECOND = timedelta(microseconds=1)


class ChatFullError(ConflictError):
    """The conversation has all the questions it takes."""

    def __init__(self) -> None:
        super().__init__(
            f"This chat already has {MAX_QUESTIONS} questions. Start a new one to keep asking."
        )


def _cursor(conversation: db.Conversation) -> str:
    return join_cursor(conversation.id, (conversation.updated_at - _EPOCH) // _MICROSECOND)


async def list_conversations(
    session: AsyncSession, *, limit: int, cursor: str | None = None
) -> tuple[list[db.Conversation], str | None]:
    """One page of conversations, most recently active first, plus the next cursor."""
    position = tuple_(db.Conversation.updated_at, db.Conversation.id)
    query = select(db.Conversation)
    if cursor is not None:
        after_id, micros = split_cursor(cursor, CONVERSATION_CURSOR)
        query = query.where(position < (_EPOCH + micros * _MICROSECOND, after_id))
    query = query.order_by(db.Conversation.updated_at.desc(), db.Conversation.id.desc())
    return await paginate(session, query, limit=limit, cursor_of=_cursor)


async def get_conversation(session: AsyncSession, conversation_id: str) -> db.Conversation:
    """A conversation with its messages loaded."""
    return await get_existing(
        session,
        db.Conversation,
        conversation_id,
        options=[selectinload(db.Conversation.messages)],
    )


async def delete_conversation(session: AsyncSession, conversation_id: str) -> None:
    """Deletes a conversation with its messages. The caller commits."""
    deleted = await session.scalar(
        delete(db.Conversation)
        .where(db.Conversation.id == conversation_id)
        .returning(db.Conversation.id)
    )
    if deleted is None:
        raise NotFoundError("Conversation")


async def _questions(session: AsyncSession, conversation_id: str) -> int:
    asked = await session.scalar(
        select(func.count()).where(
            db.Message.conversation_id == conversation_id, db.Message.role == MessageRole.USER
        )
    )
    return asked or 0


async def check_room(session: AsyncSession, conversation_id: str) -> db.Conversation:
    """The conversation, if it takes another question. Raises `NotFoundError` or `ChatFullError`."""
    conversation = await get_existing(session, db.Conversation, conversation_id)
    if await _questions(session, conversation_id) >= MAX_QUESTIONS:
        raise ChatFullError()
    return conversation


async def add_message(
    session: AsyncSession,
    conversation_id: str,
    role: MessageRole,
    content: str,
    *,
    tool_calls: Sequence[ToolCall] = (),
    sources: Sequence[Source] = (),
) -> db.Message:
    """Adds a message, which makes it the conversation's latest activity. The caller commits.

    Raises `ChatFullError` for a question past `MAX_QUESTIONS`.
    """
    # Locked, so two questions at once can't both slip under the limit.
    locked = await session.scalar(
        select(db.Conversation.id).where(db.Conversation.id == conversation_id).with_for_update()
    )
    if locked is None:
        raise NotFoundError("Conversation")
    if role is MessageRole.USER and await _questions(session, conversation_id) >= MAX_QUESTIONS:
        raise ChatFullError()
    message = db.Message(
        conversation_id=conversation_id,
        role=role,
        content=content,
        tool_calls=[call.model_dump(mode="json") for call in tool_calls],
        sources=[source.model_dump(mode="json") for source in sources],
    )
    session.add(message)
    await session.execute(
        update(db.Conversation)
        .where(db.Conversation.id == conversation_id)
        .values(updated_at=func.now())
    )
    await session.flush()
    await session.refresh(message)
    return message
