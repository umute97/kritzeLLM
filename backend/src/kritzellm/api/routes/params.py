"""Reusable path, query and header parameters."""

from typing import Annotated, Any

from fastapi import Path, Query, Request, Response

from kritzellm.domain import CONVERSATION_CURSOR, PAGE_CURSOR

from ..schemas.common import BlockId, ConversationId, Day, JobId, JournalId, PageId

JournalIdPath = Annotated[JournalId, Path(alias="journalId", description="The journal's ID.")]
PageIdPath = Annotated[PageId, Path(alias="pageId", description="The page's ID.")]
BlockIdPath = Annotated[BlockId, Path(alias="blockId", description="The block's ID.")]
JobIdPath = Annotated[JobId, Path(alias="jobId", description="The job's ID.")]
ConversationIdPath = Annotated[
    ConversationId, Path(alias="conversationId", description="The conversation's ID.")
]

Limit = Annotated[int, Query(ge=1, le=100, description="Maximum number of items to return.")]
_CURSOR = "The `nextCursor` from the previous page. Omit for the first page."
JournalCursor = Annotated[JournalId | None, Query(description=_CURSOR)]
PageCursor = Annotated[str | None, Query(pattern=PAGE_CURSOR, description=_CURSOR)]
JobCursor = Annotated[JobId | None, Query(description=_CURSOR)]
ConversationCursor = Annotated[str | None, Query(pattern=CONVERSATION_CURSOR, description=_CURSOR)]
DateFrom = Annotated[
    Day | None, Query(alias="dateFrom", description="Only entries dated on or after this day.")
]
DateTo = Annotated[
    Day | None, Query(alias="dateTo", description="Only entries dated on or before this day.")
]


def location_header(description: str) -> dict[str, Any]:
    """OpenAPI `headers` entry for a `Location` response header."""
    return {
        "Location": {
            "description": description,
            "schema": {"type": "string", "format": "uri-reference"},
        }
    }


def set_location(request: Request, response: Response, route: str, **path_params: str) -> None:
    """Points the `Location` header at another route, as a path."""
    response.headers["Location"] = request.url_for(route, **path_params).path


JOB_LOCATION = location_header("URL of the job to poll.")
BINARY = {"schema": {"type": "string", "format": "binary"}}
