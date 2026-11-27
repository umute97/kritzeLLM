"""Conversations: chat threads with the journal, and their messages."""

from enum import StrEnum
from typing import Annotated

from pydantic import Field, StringConstraints

from kritzellm.ids import SUFFIX_PATTERN, Prefix

from .common import NO_NUL, ApiModel, ConversationId, InputModel, MessageId, Timestamp

MAX_QUESTIONS = 20
"""Questions one conversation takes. Every answer rereads the whole thread, so this keeps answers
quick and cheap."""

CONVERSATION_CURSOR = rf"^{Prefix.CONVERSATION}_{SUFFIX_PATTERN}\.[0-9]{{1,17}}$"
"""A `GET /conversations` cursor: the conversation to continue after and its last activity in
microseconds since 1970, e.g. `cnv_01k7….1764262496000000`."""


class MessageRole(StrEnum):
    """Who wrote a message: you (`user`) or the journal's helper (`assistant`)."""

    USER = "user"
    ASSISTANT = "assistant"


class Message(ApiModel):
    """One message in a conversation."""

    id: MessageId
    role: MessageRole
    content: str
    created_at: Timestamp


class Conversation(ApiModel):
    """A chat thread with the journal."""

    id: ConversationId
    title: str | None = Field(max_length=200)
    """Display name; `null` until it has one."""
    created_at: Timestamp
    updated_at: Timestamp
    """Its last activity: a new message, or a new title."""


class ConversationDetail(Conversation):
    """A conversation with its messages."""

    messages: list[Message]
    """All of them, oldest first. A conversation takes up to 20 questions, each with its answer."""


class ConversationCreate(InputModel):
    """A new, empty conversation."""

    title: str | None = Field(default=None, min_length=1, max_length=200, pattern=NO_NUL)
    """Display name; leave it out to name the conversation later."""


class ConversationUpdate(InputModel):
    """Changes to a conversation. Only the given fields change."""

    title: str | None = Field(default=None, min_length=1, max_length=200, pattern=NO_NUL)
    """New display name; `null` clears it."""


class ConversationList(ApiModel):
    """A page of conversations."""

    items: list[Conversation]
    next_cursor: Annotated[str, StringConstraints(pattern=CONVERSATION_CURSOR)] | None
    """Pass as `cursor` to get the next page; `null` on the last page."""
