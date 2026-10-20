"""Reusable path, query and header parameters."""

from typing import Annotated, Any

from fastapi import Path, Query

from ..schemas.common import BlockId, Day, JobId, JournalId, PageId
from ..schemas.pages import PAGE_CURSOR

JournalIdPath = Annotated[JournalId, Path(alias="journalId", description="The journal's ID.")]
PageIdPath = Annotated[PageId, Path(alias="pageId", description="The page's ID.")]
BlockIdPath = Annotated[BlockId, Path(alias="blockId", description="The block's ID.")]
JobIdPath = Annotated[JobId, Path(alias="jobId", description="The job's ID.")]

Limit = Annotated[int, Query(ge=1, le=100, description="Maximum number of items to return.")]
_CURSOR = "The `nextCursor` from the previous page. Omit for the first page."
JournalCursor = Annotated[JournalId | None, Query(description=_CURSOR)]
PageCursor = Annotated[str | None, Query(pattern=PAGE_CURSOR, description=_CURSOR)]
JobCursor = Annotated[JobId | None, Query(description=_CURSOR)]
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


JOB_LOCATION = location_header("URL of the job to poll.")
BINARY = {"schema": {"type": "string", "format": "binary"}}
