"""Blocks: pieces of text on a page (paragraphs, lists, margin notes, ...)."""

from enum import StrEnum

from pydantic import MISSING, Field

from .common import NO_NUL, ApiModel, BlockId, InputModel, PageId
from .jobs import Job


class BlockKind(StrEnum):
    """What kind of thing a block is on the page. Drawings are described in words, in brackets."""

    HEADING = "heading"
    PARAGRAPH = "paragraph"
    LIST = "list"
    MARGIN_NOTE = "marginNote"
    DRAWING = "drawing"
    OTHER = "other"


class Block(ApiModel):
    """A piece of text on a page."""

    id: BlockId
    page_id: PageId
    seq: int = Field(ge=0)
    """Position in reading order, starting at 0."""
    kind: BlockKind
    text: str
    """The transcribed text. Unreadable words are written as `[?]`."""
    uncertain: bool
    """`true` when the model wasn't sure about parts of this block."""


class BlockInput(InputModel):
    """One block in a full replacement of a page's blocks."""

    id: BlockId | None = None
    """Set to update an existing block in place; omit to create a new one."""
    kind: BlockKind
    text: str = Field(min_length=1, max_length=20_000, pattern=NO_NUL)
    """The block's text."""
    uncertain: bool = False
    """Whether parts of the text are still unsure."""


class BlocksReplace(InputModel):
    """All blocks of a page, in reading order."""

    blocks: list[BlockInput] = Field(max_length=500)


class BlocksReplaceResult(ApiModel):
    """A page's blocks after a replacement, plus the re-index job."""

    blocks: list[Block]
    """The page's blocks after the change, in reading order."""
    job: Job


class BlockUpdate(InputModel):
    """Corrections to a single block. Only the given fields change."""

    kind: BlockKind | MISSING = MISSING
    text: str | MISSING = Field(default=MISSING, min_length=1, max_length=20_000, pattern=NO_NUL)
    """Corrected text."""
    uncertain: bool | MISSING = MISSING
    """Whether parts of the text are still unsure."""


class BlockUpdateResult(ApiModel):
    """The corrected block, plus the re-index job."""

    block: Block
    job: Job
