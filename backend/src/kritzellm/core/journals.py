"""Journals: the notebooks (or volumes) that pages belong to."""

import asyncio
from pathlib import Path

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from kritzellm.db import models as db

from .errors import NotFoundError
from .pagination import newest_first, paginate
from .storage import delete_page_files


async def list_journals(
    session: AsyncSession, *, limit: int, cursor: str | None = None
) -> tuple[list[db.Journal], str | None]:
    """One page of journals, newest first, plus the next cursor."""
    query = newest_first(select(db.Journal), db.Journal.id, cursor)
    return await paginate(session, query, limit=limit, cursor_of=lambda journal: journal.id)


async def delete_journal(session: AsyncSession, data_dir: Path, journal_id: str) -> None:
    """Deletes a journal with its pages, blocks, jobs and images.

    Commits, because the image files are only removed once the rows are gone for good.
    """
    # Locks the journal, so no pages can be added to it before it's gone.
    locked = await session.scalar(
        select(db.Journal.id).where(db.Journal.id == journal_id).with_for_update()
    )
    if locked is None:
        raise NotFoundError("Journal")
    page_ids = (
        await session.scalars(select(db.Page.id).where(db.Page.journal_id == journal_id))
    ).all()
    await session.execute(delete(db.Journal).where(db.Journal.id == journal_id))
    await session.commit()
    await asyncio.to_thread(delete_page_files, data_dir, page_ids)
