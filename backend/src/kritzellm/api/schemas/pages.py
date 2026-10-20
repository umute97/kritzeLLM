"""Pages: uploaded page images and their transcriptions."""

from enum import StrEnum
from typing import TYPE_CHECKING, Annotated, Self

from pydantic import MISSING, Field, StringConstraints

from kritzellm.ids import SUFFIX_PATTERN, Prefix

from .. import API_PREFIX
from .blocks import Block
from .common import (
    NO_NUL,
    ApiModel,
    Day,
    InputModel,
    JournalId,
    PageId,
    Problem,
    SortedDays,
    Timestamp,
)
from .jobs import Job

if TYPE_CHECKING:
    from kritzellm.db import models as db

MAX_PAGE_NUMBER = 1_000_000
"""Highest page number a client may ask for."""

PAGE_CURSOR = rf"^{Prefix.JOURNAL}_{SUFFIX_PATTERN}\.[1-9][0-9]{{0,6}}$"
"""A `GET /pages` cursor: the journal and page number to continue after, e.g. `jrn_01k7….12`."""


class PageStatus(StrEnum):
    """Where a page is in processing.

    `uploaded` (waiting for the worker) → `transcribing` → `indexing` → `ready`.
    `failed` means a step failed; see `error` and re-transcribe to retry.
    """

    UPLOADED = "uploaded"
    TRANSCRIBING = "transcribing"
    INDEXING = "indexing"
    READY = "ready"
    FAILED = "failed"


class ImageVariant(StrEnum):
    """Which version of a page image to return."""

    NORMALIZED = "normalized"
    ORIGINAL = "original"
    THUMBNAIL = "thumbnail"


class PageImageUrls(ApiModel):
    """Where to fetch each version of a page image."""

    normalized: str
    """The rotated, resized JPEG that gets transcribed."""
    original: str
    """The uploaded file as-is."""
    thumbnail: str
    """A small preview."""


class PageImage(ApiModel):
    """A page's image."""

    width: int = Field(ge=1)
    """Width of the normalized image in pixels."""
    height: int = Field(ge=1)
    """Height of the normalized image in pixels."""
    urls: PageImageUrls


class Page(ApiModel):
    """An uploaded page."""

    id: PageId
    journal_id: JournalId
    page_number: int = Field(ge=1)
    """Position of the page in its journal."""
    page_label: str | None = Field(max_length=40)
    """Page number or label as written on the page itself, if any."""
    entry_dates: list[Day]
    """Dates of the entries on this page, as read from the page or set by hand."""
    status: PageStatus
    error: Problem | None
    """Why processing failed; `null` unless `status` is `failed`."""
    image: PageImage
    transcription_model: str | None
    """Model that produced the current transcription; `null` until transcribed."""
    created_at: Timestamp
    updated_at: Timestamp

    @classmethod
    def from_db(cls, page: db.Page, **extra: object) -> Self:
        """The API view of a stored page. `extra` fills fields a subclass adds."""
        urls = {
            variant.value: f"{API_PREFIX}/pages/{page.id}/image?variant={variant.value}"
            for variant in ImageVariant
        }
        return cls.model_validate(
            {
                "id": page.id,
                "journal_id": page.journal_id,
                "page_number": page.page_number,
                "page_label": page.page_label,
                "entry_dates": page.entry_dates,
                "status": page.status,
                "error": page.error,
                "image": {"width": page.width, "height": page.height, "urls": urls},
                "transcription_model": page.transcription_model,
                "created_at": page.created_at,
                "updated_at": page.updated_at,
                **extra,
            }
        )


class PageDetail(Page):
    """A page with its transcribed blocks."""

    blocks: list[Block]
    """Transcribed blocks in reading order."""


class PageUpdate(InputModel):
    """Corrections to a page's metadata. Only the given fields change."""

    journal_id: JournalId | MISSING = MISSING
    """Move the page to this journal. Without a `pageNumber` it goes after the journal's last page."""
    page_number: int | MISSING = Field(default=MISSING, ge=1, le=MAX_PAGE_NUMBER)
    """New position in the journal. Must not be taken by another page."""
    page_label: str | None = Field(default=None, max_length=40, pattern=NO_NUL)
    """Label as written on the page; `null` clears it."""
    entry_dates: SortedDays | MISSING = Field(default=MISSING, max_length=100)
    """Corrected entry dates; `[]` clears them. Stored sorted, without repeats."""


class PageList(ApiModel):
    """A page of pages."""

    items: list[Page]
    next_cursor: Annotated[str, StringConstraints(pattern=PAGE_CURSOR)] | None
    """Pass as `cursor` to get the next page; `null` on the last page."""


class UploadItem(ApiModel):
    """The outcome for one uploaded file."""

    filename: str
    """The uploaded file's name."""
    page: Page
    duplicate: bool
    """`true` if this exact file was already in the journal (or earlier in this upload); `page` is then the existing page."""
    job: Job | None
    """The page's newest job: for a new page the `ingestPage` job to poll, for a duplicate whatever ran on it last."""


class UploadResult(ApiModel):
    """One entry per uploaded file, in upload order."""

    items: list[UploadItem]
