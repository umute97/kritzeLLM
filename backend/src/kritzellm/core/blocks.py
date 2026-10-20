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

from .jobs import enqueue, enqueue_once, pending

READING = (JobKind.INGEST_PAGE, JobKind.TRANSCRIBE_PAGE)
"""Jobs that replace a page's blocks with a fresh transcription."""


class PageBusyError(Exception):
    """The page is waiting to be read or being read, which would undo any change."""


class BlockIdError(Exception):
    """Some blocks of a replacement have ids that can't be used."""

    def __init__(self, problems: Sequence[tuple[int, str]]) -> None:
        super().__init__("Invalid block ids")
        self.problems = problems
        """The index of each offending block, with what's wrong with its id."""


async def _lock_editable(session: AsyncSession, page_id: str) -> db.Page | None:
    """Locks the page for a change. `None` if it's gone; raises `PageBusyError` while it's read."""
    page = await session.get(db.Page, page_id, with_for_update=True, populate_existing=True)
    if page is not None and await pending(session, page_id, READING):
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
) -> tuple[db.Block, db.Job] | None:
    """Applies `changes` to a block and queues its page's re-index. `None` if the block is gone.

    The caller commits.
    """
    page_id = await session.scalar(select(db.Block.page_id).where(db.Block.id == block_id))
    if page_id is None or (page := await _lock_editable(session, page_id)) is None:
        return None
    block = await session.get(db.Block, block_id, populate_existing=True)
    if block is None:
        return None  # A transcription replaced it while we waited for the lock.
    for field, value in changes.items():
        setattr(block, field, value)
    return block, await _edited(session, page)


async def replace_blocks(
    session: AsyncSession, page_id: str, blocks: Sequence[BlockInput]
) -> tuple[list[db.Block], db.Job] | None:
    """Makes `blocks` the page's blocks, in order, and queues its re-index. `None` if it's gone.

    Blocks with an id are updated in place, those without one are created, and the page's other
    blocks are deleted. Raises `BlockIdError` for ids that aren't the page's or come twice. The
    caller commits.
    """
    page = await _lock_editable(session, page_id)
    if page is None:
        return None
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


async def request_transcription(session: AsyncSession, page_id: str) -> db.Job | None:
    """Queues reading the page again. `None` if it's gone. The caller commits.

    Raises `PageBusyError` if the page is already waiting to be read or being read.
    """
    if await _lock_editable(session, page_id) is None:
        return None
    return await enqueue(session, JobKind.TRANSCRIBE_PAGE, page_id=page_id)
