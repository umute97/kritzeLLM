from typing import Annotated

from fastapi import APIRouter, Query

from kritzellm.core import search as core

from ..deps import AppSettings, Session
from ..errors import problem_responses
from ..schemas.blocks import Block
from ..schemas.common import JournalId
from ..schemas.pages import Page
from ..schemas.search import SearchHit, SearchMode, SearchResult
from .params import DateFrom, DateTo

router = APIRouter(tags=["search"], responses=problem_responses(400, 401, 422))

QUERY_TEXT = r"^[^\x00]*[^\x00\s][^\x00]*$"
"""Any text with something besides whitespace (and no NUL characters)."""


@router.get(
    "/search",
    summary="Search pages",
    responses=problem_responses(502),
)
async def search(
    session: Session,
    settings: AppSettings,
    q: Annotated[
        str,
        Query(min_length=1, max_length=500, pattern=QUERY_TEXT, description="What to look for."),
    ],
    mode: Annotated[SearchMode, Query(description="How to search.")] = SearchMode.HYBRID,
    journal_id: Annotated[
        JournalId | None, Query(alias="journalId", description="Only pages of this journal.")
    ] = None,
    date_from: DateFrom = None,
    date_to: DateTo = None,
    limit: Annotated[
        int, Query(ge=1, le=50, description="Maximum number of pages to return.")
    ] = 10,
) -> SearchResult:
    """Finds the pages best matching `q`, each with the blocks that matched.

    `hybrid` (the default) finds text by meaning and by its words. `vector` and `keyword` do one of
    each, for comparing. `exact` lists the pages with blocks containing `q` as written, ignoring case,
    in journal and page order. The date filters keep pages with at least one entry dated within the
    range. Returns `502` when the embedding model can't be reached; `keyword` and `exact` don't need it.
    """
    hits = await core.search(
        session,
        q,
        mode=mode,
        settings=settings,
        journal_id=journal_id,
        date_from=date_from,
        date_to=date_to,
        limit=limit,
    )
    return SearchResult(
        items=[
            SearchHit(
                page=Page.from_db(hit.page),
                blocks=[Block.model_validate(block) for block in hit.blocks],
                score=hit.score,
                vector_rank=hit.vector_rank,
                keyword_rank=hit.keyword_rank,
            )
            for hit in hits
        ]
    )
