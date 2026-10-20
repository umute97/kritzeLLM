"""Blocks: correcting a page's transcription by hand, or having the page read again.

Every change locks the page row first, the same lock the worker takes to save a transcription, so
an edit and a reading never land on top of each other. While a page is waiting to be read or being
read, it can't be changed.
"""

from collections.abc import Mapping, Sequence
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from kritzellm.api.schemas.blocks import BlockInput
from kritzellm.api.schemas.jobs import JobKind
from kritzellm.db import models as db

from .errors import NotFoundError, PageBusyError
from .jobs import enqueue, enqueue_once, pending

READING = (JobKind.INGEST_PAGE, JobKind.TRANSCRIBE_PAGE)
"""Jobs that replace a page's blocks with a fresh transcription."""


class BlockIdError(Exception):
    """Some blocks of a replacement have ids that can't be used."""

    def __init__(self, problems: Sequence[tuple[int, str]]) -> None:
        super().__init__("Invalid block ids")
        self.problems = problems
        """The index of each offending block, with what's wrong with its id."""


async def _lock_editable(session: AsyncSession, page_id: str, *, what: str = "Page") -> db.Page:
    """Locks the page for a change.

    Raises `NotFoundError` (about `what`) if the page is gone, and `PageBusyError` while it's read.
    """
    page = await session.get(db.Page, page_id, with_for_update=True, populate_existing=True)
    if page is None:
        raise NotFoundError(what)
    if await pending(session, page_id, READING):
        raise PageBusyError
    return page


async def _edited(session: AsyncSession, page: db.Page) -> db.Job:
    """Marks the page as changed and returns the job that re-indexes it."""
    page.updated_at = func.now()
    job = await enqueue_once(session, JobKind.REINDEX_PAGE, page_id=page.id)
    await session.flush()
    return job


async def update_block(
    session: AsyncSession, block_id: str, changes: Mapping[str, Any]
) -> tuple[db.Block, db.Job]:
    """Applies `changes` to a block and queues its page's re-index. The caller commits."""
    page_id = await session.scalar(select(db.Block.page_id).where(db.Block.id == block_id))
    if page_id is None:
        raise NotFoundError("Block")
    page = await _lock_editable(session, page_id, what="Block")
    block = await session.get(db.Block, block_id, populate_existing=True)
    if block is None:
        raise NotFoundError("Block")  # A transcription replaced it while we waited for the lock.
    for field, value in changes.items():
        setattr(block, field, value)
    return block, await _edited(session, page)


async def replace_blocks(
    session: AsyncSession, page_id: str, blocks: Sequence[BlockInput]
) -> tuple[list[db.Block], db.Job]:
    """Makes `blocks` the page's blocks, in order, and queues its re-index.

    Blocks with an id are updated in place, those without one are created, and the page's other
    blocks are deleted. Raises `BlockIdError` for ids that aren't the page's or come twice. The
    caller commits.
    """
    page = await _lock_editable(session, page_id)
    existing = {
        block.id: block
        for block in await session.scalars(select(db.Block).where(db.Block.page_id == page_id))
    }
    problems: list[tuple[int, str]] = []
    seen: set[str] = set()
    for index, block in enumerate(blocks):
        if block.id is None:
            continue
        if block.id not in existing:
            problems.append((index, "Not a block of this page"))
        elif block.id in seen:
            problems.append((index, "This block is given more than once"))
        seen.add(block.id)
    if problems:
        raise BlockIdError(problems)

    for block_id in existing.keys() - seen:
        await session.delete(existing[block_id])
    # `(page_id, seq)` is only checked on commit, so blocks may swap places in between.
    replaced = []
    for seq, item in enumerate(blocks):
        block = existing[item.id] if item.id else db.Block(page_id=page_id)
        block.seq = seq
        block.kind, block.text, block.uncertain = item.kind, item.text, item.uncertain
        session.add(block)
        replaced.append(block)
    return replaced, await _edited(session, page)


async def request_transcription(session: AsyncSession, page_id: str) -> db.Job:
    """Queues reading the page again. The caller commits.

    Raises `PageBusyError` if the page is already waiting to be read or being read.
    """
    await _lock_editable(session, page_id)
    return await enqueue(session, JobKind.TRANSCRIBE_PAGE, page_id=page_id)
