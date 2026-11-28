"""Journals: notebooks (or volumes) that pages belong to."""

from typing import Annotated

from pydantic import MISSING, Field

from kritzellm.domain import JOURNAL_NAME_LENGTH

from .common import NO_NUL, ApiModel, InputModel, JournalId, Timestamp

DESCRIPTION_LENGTH = 2000

NameInput = Annotated[str, Field(min_length=1, max_length=JOURNAL_NAME_LENGTH, pattern=NO_NUL)]
DescriptionInput = Annotated[str, Field(max_length=DESCRIPTION_LENGTH, pattern=NO_NUL)]


class Journal(ApiModel):
    """A notebook (or volume) of handwritten pages."""

    id: JournalId
    name: str = Field(min_length=1, max_length=JOURNAL_NAME_LENGTH)
    """Display name."""
    description: str | None = Field(max_length=DESCRIPTION_LENGTH)
    """Optional notes about the journal."""
    page_count: int = Field(ge=0)
    """Number of pages in the journal."""
    created_at: Timestamp
    updated_at: Timestamp


class JournalCreate(InputModel):
    """A new journal."""

    name: NameInput
    """Display name."""
    description: DescriptionInput | None = None
    """Optional notes about the journal."""


class JournalUpdate(InputModel):
    """Changes to a journal. Only the given fields change."""

    name: NameInput | MISSING = MISSING
    """New display name."""
    description: DescriptionInput | None = None
    """New notes; `null` clears them."""


class JournalList(ApiModel):
    """A page of journals."""

    items: list[Journal]
    next_cursor: JournalId | None
    """Pass as `cursor` to get the next page; `null` on the last page."""
