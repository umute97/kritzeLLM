"""Journals: the notebooks (or volumes) that pages belong to."""

import asyncio
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from kritzellm.db import models as db

from .errors import NotFoundError, get_existing
from .pagination import paginate
from .storage import delete_page_files


async def list_journals(
    session: AsyncSession, *, limit: int, cursor: str | None = None
) -> tuple[list[db.Journal], str | None]:
    """One page of journals, newest first, plus the next cursor."""
    rows, next_cursor = await paginate(
        session, select(db.Journal), id_column=db.Journal.id, limit=limit, cursor=cursor
    )
    return [journal for (journal,) in rows], next_cursor


async def create_journal(
    session: AsyncSession, *, name: str, description: str | None = None
) -> db.Journal:
    """Adds an empty journal. The caller commits."""
    journal = db.Journal(name=name, description=description)
    session.add(journal)
    await session.flush()
    await session.refresh(journal)
    return journal


async def update_journal(
    session: AsyncSession, journal_id: str, changes: Mapping[str, Any]
) -> db.Journal:
    """Applies `changes` (name, description) to a journal. The caller commits."""
    journal = await get_existing(session, db.Journal, journal_id)
    for field, value in changes.items():
        setattr(journal, field, value)
    await session.flush()
    await session.refresh(journal)
    return journal


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
