"""The journal's vocabulary: what pages, blocks, jobs and messages can be, and the limits on them."""

from enum import StrEnum

from kritzellm.ids import SUFFIX_PATTERN, Prefix


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


class BlockKind(StrEnum):
    """What kind of thing a block is on the page. Drawings are described in words, in brackets."""

    HEADING = "heading"
    PARAGRAPH = "paragraph"
    LIST = "list"
    MARGIN_NOTE = "marginNote"
    DRAWING = "drawing"
    OTHER = "other"


class JobKind(StrEnum):
    """What a job does."""

    INGEST_PAGE = "ingestPage"
    TRANSCRIBE_PAGE = "transcribePage"
    REINDEX_PAGE = "reindexPage"
    REINDEX_ALL = "reindexAll"


class JobStatus(StrEnum):
    """Lifecycle of a job."""

    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class MessageRole(StrEnum):
    """Who wrote a message: you (`user`) or the journal's helper (`assistant`)."""

    USER = "user"
    ASSISTANT = "assistant"


class SearchMode(StrEnum):
    """How to search.

    `hybrid` merges `vector` and `keyword` results with reciprocal rank fusion. `vector` finds text
    by meaning, `keyword` by its words (`"quoted phrases"`, `or` and `-word` work). `exact` finds
    blocks containing the query as written, ignoring case.
    """

    HYBRID = "hybrid"
    VECTOR = "vector"
    KEYWORD = "keyword"
    EXACT = "exact"


JOURNAL_NAME_LENGTH = 120
PAGE_LABEL_LENGTH = 40
CONVERSATION_TITLE_LENGTH = 200

MAX_QUESTIONS = 20
"""Questions one conversation takes. Every answer rereads the whole thread, so this keeps answers
quick and cheap."""

EMBED_DIMENSIONS = 1536
"""Length of every stored vector: `text-embedding-3-small`'s own, and asked of other models too."""

PAGE_CURSOR = rf"^{Prefix.JOURNAL}_{SUFFIX_PATTERN}\.[1-9][0-9]{{0,6}}$"
"""A `GET /pages` cursor: the journal and page number to continue after, e.g. `jrn_01k7….12`."""

CONVERSATION_CURSOR = rf"^{Prefix.CONVERSATION}_{SUFFIX_PATTERN}\.[0-9]{{1,17}}$"
"""A `GET /conversations` cursor: the conversation to continue after and its last activity in
microseconds since 1970, e.g. `cnv_01k7….1764262496000000`."""
