"""Searching the indexed pages: by meaning (vector), by words (keyword), both (hybrid), or exactly.

Hybrid search merges the vector and keyword rankings of chunks with reciprocal rank fusion. Each
page shows up once, with its best chunk.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date

from sqlalchemy import ColumnElement, Select, func, literal_column, null, select, text
from sqlalchemy.dialects.postgresql import distinct_on
from sqlalchemy.ext.asyncio import AsyncSession

from kritzellm.api.schemas.search import SearchMode
from kritzellm.config import Settings
from kritzellm.db import models as db

from .embeddings import embed_query
from .pages import dated_within

CANDIDATES = 30
"""How many chunks each ranking contributes before fusing."""

RRF_K = 60
"""Reciprocal rank fusion's damping constant: a chunk scores `1 / (RRF_K + rank)` per ranking."""


@dataclass(frozen=True, slots=True)
class Hit:
    page: db.Page
    blocks: list[db.Block]
    score: float
    vector_rank: int | None
    keyword_rank: int | None


async def search(
    session: AsyncSession,
    query: str,
    *,
    mode: SearchMode,
    settings: Settings,
    journal_id: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    limit: int,
) -> list[Hit]:
    """The pages best matching `query`, best first.

    Raises `UpstreamError` if the query can't be embedded (`hybrid` and `vector` only).
    """
    filters = _page_filters(journal_id, date_from, date_to)
    if mode is SearchMode.EXACT:
        return await _exact(session, query, filters, limit)

    vector = keyword = None
    if mode is not SearchMode.KEYWORD:
        embedding = await embed_query(query, settings)
        # Keeps scanning the HNSW index until enough chunks pass the filters.
        await session.execute(text("SET LOCAL hnsw.iterative_scan = strict_order"))
        vector = _vector_ranking(embedding, settings.embed_model, filters).cte("vector")
    if mode is not SearchMode.VECTOR:
        keyword = _keyword_ranking(query, filters).cte("keyword")

    if vector is not None and keyword is not None:
        both = vector.join(
            keyword,
            (vector.c.page_id == keyword.c.page_id) & (vector.c.seq == keyword.c.seq),
            full=True,
        )
        fused = select(
            func.coalesce(vector.c.page_id, keyword.c.page_id).label("page_id"),
            func.coalesce(vector.c.seq, keyword.c.seq).label("seq"),
            (
                func.coalesce(1.0 / (RRF_K + vector.c.rank), 0.0)
                + func.coalesce(1.0 / (RRF_K + keyword.c.rank), 0.0)
            ).label("score"),
            vector.c.rank.label("vector_rank"),
            keyword.c.rank.label("keyword_rank"),
        ).select_from(both)
    elif vector is not None:
        fused = select(
            vector.c.page_id,
            vector.c.seq,
            vector.c.score,
            vector.c.rank.label("vector_rank"),
            null().label("keyword_rank"),
        )
    else:
        assert keyword is not None
        fused = select(
            keyword.c.page_id,
            keyword.c.seq,
            keyword.c.score,
            null().label("vector_rank"),
            keyword.c.rank.label("keyword_rank"),
        )

    ranked = fused.subquery("ranked")
    best = (
        select(ranked)
        .ext(distinct_on(ranked.c.page_id))
        .order_by(ranked.c.page_id, ranked.c.score.desc(), ranked.c.seq)
        .subquery("best")
    )
    rows = await session.execute(
        select(best, db.Chunk.block_ids)
        .join(db.Chunk, (db.Chunk.page_id == best.c.page_id) & (db.Chunk.seq == best.c.seq))
        .order_by(best.c.score.desc(), best.c.page_id)
        .limit(limit)
    )
    matches = rows.all()
    pages = await _pages(session, [match.page_id for match in matches])
    blocks = await _blocks(session, [block_id for match in matches for block_id in match.block_ids])
    hits = []
    for match in matches:
        # Blocks deleted since the page was indexed (while it's being read again) are left out.
        found = [blocks[block_id] for block_id in match.block_ids if block_id in blocks]
        if found and match.page_id in pages:
            hits.append(
                Hit(
                    page=pages[match.page_id],
                    blocks=sorted(found, key=lambda block: block.seq),
                    score=float(match.score),
                    vector_rank=match.vector_rank,
                    keyword_rank=match.keyword_rank,
                )
            )
    return hits


def _page_filters(
    journal_id: str | None, date_from: date | None, date_to: date | None
) -> list[ColumnElement[bool]]:
    """Conditions on `db.Page` that every hit's page must meet."""
    filters = []
    if journal_id is not None:
        filters.append(db.Page.journal_id == journal_id)
    if date_from is not None or date_to is not None:
        filters.append(dated_within(date_from, date_to))
    return filters


def _vector_ranking(
    embedding: Sequence[float], model: str, filters: Sequence[ColumnElement[bool]]
) -> Select:
    """The chunks closest in meaning. Only chunks embedded by `model` are comparable."""
    distance = db.Chunk.embedding.cosine_distance(embedding)
    return (
        select(
            db.Chunk.page_id,
            db.Chunk.seq,
            func.row_number().over(order_by=distance).label("rank"),
            (1 - distance).label("score"),
        )
        .join(db.Page, db.Page.id == db.Chunk.page_id)
        .where(db.Chunk.embed_model == model, *filters)
        .order_by(distance)
        .limit(CANDIDATES)
    )


def _keyword_ranking(query: str, filters: Sequence[ColumnElement[bool]]) -> Select:
    """The chunks whose words best match the query, in web search syntax."""
    config = literal_column(f"'{db.TEXT_SEARCH_CONFIG}'::regconfig")
    tsquery = func.websearch_to_tsquery(config, query)
    score = func.ts_rank_cd(db.Chunk.tsv, tsquery)
    order = (score.desc(), db.Chunk.page_id, db.Chunk.seq)
    return (
        select(
            db.Chunk.page_id,
            db.Chunk.seq,
            func.row_number().over(order_by=order).label("rank"),
            score.label("score"),
        )
        .join(db.Page, db.Page.id == db.Chunk.page_id)
        .where(db.Chunk.tsv.bool_op("@@")(tsquery), *filters)
        .order_by(*order)
        .limit(CANDIDATES)
    )


def _like_pattern(query: str) -> str:
    """An `ILIKE` pattern matching `query` anywhere, with its wildcards taken literally."""
    escaped = query.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{escaped}%"


async def _exact(
    session: AsyncSession, query: str, filters: Sequence[ColumnElement[bool]], limit: int
) -> list[Hit]:
    """Pages with blocks containing `query` as written (ignoring case), in `GET /pages` order."""
    contains = db.Block.text.ilike(_like_pattern(query), escape="\\")
    rows = await session.execute(
        select(db.Block.page_id, func.count().label("matches"))
        .join(db.Page, db.Page.id == db.Block.page_id)
        .where(contains, *filters)
        .group_by(db.Block.page_id, db.Page.journal_id, db.Page.page_number)
        .order_by(db.Page.journal_id.desc(), db.Page.page_number)
        .limit(limit)
    )
    matches = rows.all()
    page_ids = [match.page_id for match in matches]
    pages = await _pages(session, page_ids)
    blocks = await session.scalars(
        select(db.Block)
        .where(db.Block.page_id.in_(page_ids), contains)
        .order_by(db.Block.page_id, db.Block.seq)
    )
    by_page: dict[str, list[db.Block]] = {}
    for block in blocks:
        by_page.setdefault(block.page_id, []).append(block)
    return [
        Hit(
            page=pages[match.page_id],
            blocks=by_page[match.page_id],
            score=float(match.matches),
            vector_rank=None,
            keyword_rank=None,
        )
        for match in matches
        if match.page_id in pages and match.page_id in by_page
    ]


async def _pages(session: AsyncSession, page_ids: Sequence[str]) -> dict[str, db.Page]:
    pages = await session.scalars(select(db.Page).where(db.Page.id.in_(page_ids)))
    return {page.id: page for page in pages}


async def _blocks(session: AsyncSession, block_ids: Sequence[str]) -> dict[str, db.Block]:
    blocks = await session.scalars(select(db.Block).where(db.Block.id.in_(block_ids)))
    return {block.id: block for block in blocks}
