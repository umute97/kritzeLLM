"""Conversations: chat threads with the journal, and the messages in them."""

import re
from collections.abc import Mapping
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import and_, delete, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from kritzellm.api.schemas.conversations import CONVERSATION_CURSOR, MAX_QUESTIONS, MessageRole
from kritzellm.db import models as db

from .errors import ConflictError, NotFoundError, get_existing

_EPOCH = datetime(1970, 1, 1, tzinfo=UTC)
_MICROSECOND = timedelta(microseconds=1)


class ChatFullError(ConflictError):
    """The conversation has all the questions it takes."""

    def __init__(self) -> None:
        super().__init__(
            f"This chat already has {MAX_QUESTIONS} questions. Start a new one to keep asking."
        )


def encode_cursor(conversation: db.Conversation) -> str:
    """A cursor for the position right after `conversation`."""
    return f"{conversation.id}.{(conversation.updated_at - _EPOCH) // _MICROSECOND}"


def decode_cursor(cursor: str) -> tuple[str, datetime]:
    """The conversation ID and last activity in a cursor. Raises `ValueError` if it isn't one."""
    if not re.fullmatch(CONVERSATION_CURSOR, cursor):
        raise ValueError("Not a conversation cursor")
    conversation_id, _, micros = cursor.partition(".")
    return conversation_id, _EPOCH + int(micros) * _MICROSECOND


async def list_conversations(
    session: AsyncSession, *, limit: int, cursor: str | None = None
) -> tuple[list[db.Conversation], str | None]:
    """One page of conversations, most recently active first, plus the next cursor."""
    activity, conversation_id = db.Conversation.updated_at, db.Conversation.id
    query = select(db.Conversation)
    if cursor is not None:
        after_id, after_activity = decode_cursor(cursor)
        query = query.where(
            or_(
                activity < after_activity,
                and_(activity == after_activity, conversation_id < after_id),
            )
        )
    query = query.order_by(activity.desc(), conversation_id.desc()).limit(limit + 1)
    conversations = list((await session.scalars(query)).all())
    if len(conversations) <= limit:
        return conversations, None
    return conversations[:limit], encode_cursor(conversations[limit - 1])


async def create_conversation(
    session: AsyncSession, *, title: str | None = None
) -> db.Conversation:
    """Adds an empty conversation. The caller commits."""
    conversation = db.Conversation(title=title)
    session.add(conversation)
    await session.flush()
    await session.refresh(conversation)
    return conversation


async def get_conversation(session: AsyncSession, conversation_id: str) -> db.Conversation:
    """A conversation with its messages loaded."""
    return await get_existing(
        session,
        db.Conversation,
        conversation_id,
        options=[selectinload(db.Conversation.messages)],
    )


async def update_conversation(
    session: AsyncSession, conversation_id: str, changes: Mapping[str, Any]
) -> db.Conversation:
    """Applies `changes` (the title) to a conversation. The caller commits."""
    conversation = await get_existing(session, db.Conversation, conversation_id)
    for field, value in changes.items():
        setattr(conversation, field, value)
    await session.flush()
    await session.refresh(conversation)
    return conversation


async def delete_conversation(session: AsyncSession, conversation_id: str) -> None:
    """Deletes a conversation with its messages. The caller commits."""
    deleted = await session.scalar(
        delete(db.Conversation)
        .where(db.Conversation.id == conversation_id)
        .returning(db.Conversation.id)
    )
    if deleted is None:
        raise NotFoundError("Conversation")


async def add_message(
    session: AsyncSession, conversation_id: str, role: MessageRole, content: str
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
    if role is MessageRole.USER:
        asked = await session.scalar(
            select(func.count()).where(
                db.Message.conversation_id == conversation_id, db.Message.role == MessageRole.USER
            )
        )
        if asked is not None and asked >= MAX_QUESTIONS:
            raise ChatFullError()
    message = db.Message(conversation_id=conversation_id, role=role, content=content)
    session.add(message)
    await session.execute(
        update(db.Conversation)
        .where(db.Conversation.id == conversation_id)
        .values(updated_at=func.now())
    )
    await session.flush()
    await session.refresh(message)
    return message
