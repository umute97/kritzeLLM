"""What the helper can look up: the API's own searches and pages, written out for the model.

Every block a tool shows gets its citation number, so the answer can point at it.
"""

import re
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import date

from pydantic_ai import RunContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from kritzellm.config import Settings
from kritzellm.db import models as db
from kritzellm.domain import BlockKind, PageStatus, SearchMode
from kritzellm.ids import SUFFIX_PATTERN, Prefix

from .. import pages as pages_core
from .. import search as search_core
from ..errors import UpstreamError
from .citations import Citations

SEARCH_HITS = 8
EXACT_HITS = 10
LISTED_PAGES = 40
AROUND = 2
"""Blocks shown on each side of the one `read_block` is asked for."""

_PAGE_ID = re.compile(rf"{Prefix.PAGE}_{SUFFIX_PATTERN}")


@dataclass
class Deps:
    session: AsyncSession
    settings: Settings
    journals: dict[str, str]
    """Every journal's name, by ID."""
    citations: Citations = field(default_factory=Citations)
    pages_found: dict[str, int] = field(default_factory=dict)
    """How many pages each tool call came back with, by tool call ID."""


Context = RunContext[Deps]


def _found(ctx: Context, pages: int) -> None:
    if ctx.tool_call_id is not None:
        ctx.deps.pages_found[ctx.tool_call_id] = pages


def _page_heading(ctx: Context, page: db.Page) -> str:
    journal = ctx.deps.journals.get(page.journal_id, "a journal")
    dates = ", ".join(day.isoformat() for day in page.entry_dates) or "no date"
    return f"Page {page.page_number} of {journal} ({dates}; id {page.id})"


def _block_line(ctx: Context, block: db.Block, page: db.Page) -> str:
    kind = "" if block.kind == BlockKind.PARAGRAPH else f"({block.kind}) "
    return f"[{ctx.deps.citations.ref(block, page)}] {kind}{block.text}"


def _page_text(ctx: Context, page: db.Page, blocks: Sequence[db.Block]) -> str:
    return "\n".join([_page_heading(ctx, page), *(_block_line(ctx, b, page) for b in blocks)])


def _unknown_journal(ctx: Context, journal_id: str | None) -> str | None:
    if journal_id is None or journal_id in ctx.deps.journals:
        return None
    return f"There's no journal with the id {journal_id}. Use one of the IDs you were given."


def _hits_text(ctx: Context, hits: Sequence[search_core.Hit]) -> str:
    _found(ctx, len(hits))
    if not hits:
        return "Nothing matched."
    return "\n\n".join(_page_text(ctx, hit.page, hit.blocks) for hit in hits)


async def search_journal(
    ctx: Context,
    query: str,
    journal_id: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
) -> str:
    """Finds the pages that best match a query, by meaning and by words, best first, each with
    the passage that matched.

    Args:
        query: What to look for, e.g. `planting sweet peas` or `rainy Sunday at the lake`.
        journal_id: Only pages of this journal.
        date_from: Only pages with an entry on or after this day.
        date_to: Only pages with an entry on or before this day.
    """
    if problem := _unknown_journal(ctx, journal_id):
        return problem
    deps = ctx.deps

    async def search(mode: SearchMode) -> list[search_core.Hit]:
        return await search_core.search(
            deps.session,
            query,
            mode=mode,
            settings=deps.settings,
            journal_id=journal_id,
            date_from=date_from,
            date_to=date_to,
            limit=SEARCH_HITS,
        )

    try:
        return _hits_text(ctx, await search(SearchMode.HYBRID))
    except UpstreamError:
        note = "Searching by meaning isn't available right now, so this only matched words.\n\n"
        return note + _hits_text(ctx, await search(SearchMode.KEYWORD))


async def find_exact(ctx: Context, text: str, journal_id: str | None = None) -> str:
    """Finds the blocks that contain some text exactly as written (ignoring case), e.g. a name
    or a phrase, in journal and page order.

    Args:
        text: The exact text to look for.
        journal_id: Only pages of this journal.
    """
    if problem := _unknown_journal(ctx, journal_id):
        return problem
    hits = await search_core.search(
        ctx.deps.session,
        text,
        mode=SearchMode.EXACT,
        settings=ctx.deps.settings,
        journal_id=journal_id,
        limit=EXACT_HITS,
    )
    return _hits_text(ctx, hits)


async def list_pages(
    ctx: Context,
    journal_id: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
) -> str:
    """Lists pages without their text, to browse a journal or a stretch of time. Read the ones
    you need with `read_page`.

    Args:
        journal_id: Only pages of this journal.
        date_from: Only pages with an entry on or after this day.
        date_to: Only pages with an entry on or before this day.
    """
    if problem := _unknown_journal(ctx, journal_id):
        return problem
    pages, more = await pages_core.list_pages(
        ctx.deps.session,
        journal_id=journal_id,
        status=PageStatus.READY,
        date_from=date_from,
        date_to=date_to,
        limit=LISTED_PAGES,
    )
    _found(ctx, len(pages))
    if not pages:
        return "No pages."
    lines = [_page_heading(ctx, page) for page in pages]
    if more:
        lines.append("… and more. Narrow it down by journal or dates to see them.")
    return "\n".join(lines)


async def read_page(ctx: Context, page_id: str) -> str:
    """Reads a whole page, every block in reading order.

    Args:
        page_id: The page's ID, e.g. `pg_01k7c9a3b5d7e9f1g3h5j7k9m1`.
    """
    page = None
    if _PAGE_ID.fullmatch(page_id):
        # A page a search already loaded is loaded again, now with its blocks.
        page = await ctx.deps.session.get(
            db.Page, page_id, options=[selectinload(db.Page.blocks)], populate_existing=True
        )
    if page is None:
        _found(ctx, 0)
        return f"There's no page with the id {page_id}."
    _found(ctx, 1)
    if not page.blocks:
        empty = "It has no text." if page.status == PageStatus.READY else "It hasn't been read yet."
        return f"{_page_heading(ctx, page)}\n{empty}"
    return _page_text(ctx, page, page.blocks)


async def read_block(ctx: Context, ref: int) -> str:
    """Reads what's around a block you've already seen: the block with up to two blocks before
    and after it on its page.

    Args:
        ref: The block's number, as in `[3]`.
    """
    source = ctx.deps.citations.get(ref)
    page = await ctx.deps.session.get(db.Page, source.page_id) if source else None
    block = await ctx.deps.session.get(db.Block, source.block_id) if source else None
    if source is None or page is None or block is None:
        _found(ctx, 0)
        return f"There's no block [{ref}] to read around."
    blocks = await ctx.deps.session.scalars(
        select(db.Block)
        .where(
            db.Block.page_id == page.id,
            db.Block.seq.between(block.seq - AROUND, block.seq + AROUND),
        )
        .order_by(db.Block.seq)
    )
    _found(ctx, 1)
    return _page_text(ctx, page, blocks.all())


TOOLS = (search_journal, find_exact, list_pages, read_page, read_block)
