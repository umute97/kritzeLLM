"""Conversations: chat threads with the journal, and their messages."""

from enum import StrEnum
from typing import Annotated, Any, Literal

from pydantic import ConfigDict, Field, RootModel, StringConstraints

from kritzellm.ids import SUFFIX_PATTERN, Prefix

from .common import (
    NO_NUL,
    ApiModel,
    BlockId,
    ConversationId,
    Day,
    InputModel,
    JournalId,
    MessageId,
    PageId,
    Problem,
    Timestamp,
)

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


class ToolCall(ApiModel):
    """Something the helper looked up while answering."""

    name: str
    """The tool, e.g. `search_journal` or `read_page`."""
    args: dict[str, Any]
    """What it was called with."""
    pages: int = Field(ge=0)
    """How many pages it came back with."""


class Source(ApiModel):
    """A block an answer cites, as it read when the answer was written."""

    ref: int = Field(ge=1)
    """The number the answer cites it with, as in `[3]`."""
    block_id: BlockId
    page_id: PageId
    journal_id: JournalId
    page_number: int = Field(ge=1)
    entry_dates: list[Day]
    quote: str
    """The block's text."""


class Message(ApiModel):
    """One message in a conversation."""

    id: MessageId
    role: MessageRole
    content: str
    """The text. An answer cites its sources as `[n]`, the `ref` of one of its `sources`."""
    tool_calls: list[ToolCall]
    """What the helper looked up for an answer, in order; empty for questions."""
    sources: list[Source]
    """The blocks an answer cites, in the order it first cites them; empty for questions."""
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


QUESTION_TEXT = r"^[^\x00]*[^\x00\s][^\x00]*$"
"""Any text with something besides whitespace (and no NUL characters)."""


class Question(InputModel):
    """A question for the journal."""

    content: str = Field(min_length=1, max_length=4000, pattern=QUESTION_TEXT)


class ConversationList(ApiModel):
    """A page of conversations."""

    items: list[Conversation]
    next_cursor: Annotated[str, StringConstraints(pattern=CONVERSATION_CURSOR)] | None
    """Pass as `cursor` to get the next page; `null` on the last page."""


class _Event(ApiModel):
    # Sent, never received: its `type` is always there.
    model_config = ConfigDict(json_schema_serialization_defaults_required=True)


class MessageStartEvent(_Event):
    """The helper started on an answer."""

    type: Literal["messageStart"] = "messageStart"


class ToolCallEvent(_Event):
    """The helper is looking something up."""

    type: Literal["toolCall"] = "toolCall"
    id: str
    """Matches the `toolResult` that follows."""
    name: str
    args: dict[str, Any]


class ToolResultEvent(_Event):
    """A lookup came back."""

    type: Literal["toolResult"] = "toolResult"
    id: str
    name: str
    pages: int = Field(ge=0)
    """How many pages it came back with."""


class TextDeltaEvent(_Event):
    """More of the answer's text. Until `messageEnd`, it may still cite sources that get dropped."""

    type: Literal["textDelta"] = "textDelta"
    text: str


class SourceEvent(_Event):
    """A block the finished answer cites."""

    type: Literal["source"] = "source"
    source: Source


class MessageEndEvent(_Event):
    """The saved answer, exactly as JSON mode returns it. Its `content` replaces the streamed text."""

    type: Literal["messageEnd"] = "messageEnd"
    message: Message


class ErrorEvent(_Event):
    """The answer failed partway; nothing was saved."""

    type: Literal["error"] = "error"
    problem: Problem


StreamEvent = (
    MessageStartEvent
    | ToolCallEvent
    | ToolResultEvent
    | TextDeltaEvent
    | SourceEvent
    | MessageEndEvent
    | ErrorEvent
)


class ChatStreamEvent(RootModel[Annotated[StreamEvent, Field(discriminator="type")]]):
    """One server-sent event while an answer is written: `event` names its `type`, `data` is this
    object as JSON. The stream ends with `messageEnd` or `error`."""
