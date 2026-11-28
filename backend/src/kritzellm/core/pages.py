"""Pages: listing, correcting and deleting them, tracking their processing, saving their text."""

import asyncio
from collections.abc import Mapping
from datetime import date
from pathlib import Path
from typing import Any

from sqlalchemy import ColumnElement, and_, delete, func, or_, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from kritzellm.db import models as db
from kritzellm.domain import PAGE_CURSOR, PageStatus

from .errors import ConflictError, NotFoundError, PageNumberTakenError
from .pagination import join_cursor, paginate, split_cursor
from .rows import get_existing
from .storage import delete_page_files
from .transcribe import PageTranscription


def dated_within(date_from: date | None, date_to: date | None) -> ColumnElement[bool]:
    """Whether a page has at least one entry date in the range (either end may be open)."""
    day = func.unnest(db.Page.entry_dates).column_valued()
    in_range = select(day)
    if date_from is not None:
        in_range = in_range.where(day >= date_from)
    if date_to is not None:
        in_range = in_range.where(day <= date_to)
    return in_range.exists()


async def list_pages(
    session: AsyncSession,
    *,
    journal_id: str | None = None,
    status: PageStatus | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    limit: int,
    cursor: str | None = None,
) -> tuple[list[db.Page], str | None]:
    """One page of pages, newest journal first and then by page number, plus the next cursor.

    A date filter keeps pages with at least one entry date in the range.
    """
    query = select(db.Page)
    if journal_id is not None:
        query = query.where(db.Page.journal_id == journal_id)
    if status is not None:
        query = query.where(db.Page.status == status)
    if date_from is not None or date_to is not None:
        query = query.where(dated_within(date_from, date_to))
    if cursor is not None:
        after_journal, after_number = split_cursor(cursor, PAGE_CURSOR)
        query = query.where(
            or_(
                db.Page.journal_id < after_journal,
                and_(db.Page.journal_id == after_journal, db.Page.page_number > after_number),
            )
        )
    query = query.order_by(db.Page.journal_id.desc(), db.Page.page_number)
    return await paginate(
        session,
        query,
        limit=limit,
        cursor_of=lambda page: join_cursor(page.journal_id, page.page_number),
    )


async def next_page_number(session: AsyncSession, journal_id: str) -> int:
    """The number after the journal's highest one."""
    highest = await session.scalar(
        select(func.max(db.Page.page_number)).where(db.Page.journal_id == journal_id)
    )
    return (highest or 0) + 1


async def page_number_taken(
    session: AsyncSession, journal_id: str, first: int, last: int, *, besides: str | None = None
) -> bool:
    """Whether a page of the journal (other than `besides`) has a number in `first..last`."""
    query = select(db.Page.id).where(
        db.Page.journal_id == journal_id, db.Page.page_number.between(first, last)
    )
    if besides is not None:
        query = query.where(db.Page.id != besides)
    return await session.scalar(query.limit(1)) is not None


async def set_status(
    session: AsyncSession,
    page_id: str,
    status: PageStatus,
    *,
    error: dict[str, Any] | None = None,
) -> bool:
    """Moves a page to `status` (with the problem if it failed). `False` if the page is gone."""
    updated = await session.scalar(
        update(db.Page)
        .where(db.Page.id == page_id)
        .values(status=status, error=error)
        .returning(db.Page.id)
    )
    return updated is not None


async def save_transcription(
    session: AsyncSession, page_id: str, transcription: PageTranscription, model: str
) -> bool:
    """Replaces the page's blocks with a fresh transcription by `model`. `False` if the page is gone.

    The page label and entry dates are only filled in while they're still empty, so whatever was
    set by hand wins.
    """
    page = await session.get(db.Page, page_id, with_for_update=True, populate_existing=True)
    if page is None:
        return False
    await session.execute(delete(db.Block).where(db.Block.page_id == page_id))
    session.add_all(
        db.Block(
            page_id=page_id, seq=seq, kind=block.kind, text=block.text, uncertain=block.uncertain
        )
        for seq, block in enumerate(transcription.blocks)
    )
    page.transcription_model = model
    if page.page_label is None:
        page.page_label = transcription.page_label or None
    if not page.entry_dates:
        page.entry_dates = transcription.entry_dates
    await session.flush()
    return True


async def update_page(session: AsyncSession, page_id: str, changes: Mapping[str, Any]) -> db.Page:
    """Corrects a page's metadata or moves it to another journal, then commits.

    A moved page goes after the target journal's last page unless `changes` has a page number.
    Raises `ConflictError` if that journal already has the same image, and `PageNumberTakenError`
    if the number is taken there.
    """
    page = await get_existing(session, db.Page, page_id)
    changes = dict(changes)
    journal_id = changes.get("journal_id", page.journal_id)
    if journal_id != page.journal_id:
        await get_existing(session, db.Journal, journal_id)
        twin = select(db.Page.id).where(
            db.Page.journal_id == journal_id, db.Page.sha256 == page.sha256
        )
        if await session.scalar(twin) is not None:
            raise ConflictError("That journal already has a page with this image.")
        changes.setdefault("page_number", await next_page_number(session, journal_id))
    if (number := changes.get("page_number")) is not None and await page_number_taken(
        session, journal_id, number, number, besides=page.id
    ):
        raise PageNumberTakenError(f"Page number {number} is taken in that journal.")

    for field, value in changes.items():
        setattr(page, field, value)
    try:
        # Page numbers are only checked for clashes on commit.
        await session.commit()
    except IntegrityError:
        await session.rollback()
        raise ConflictError(
            "Another change to that journal got in first. Please try again."
        ) from None
    await session.refresh(page)
    return page


async def delete_page(session: AsyncSession, data_dir: Path, page_id: str) -> None:
    """Deletes a page with its blocks, jobs and images.

    Commits, because the image files are only removed once the row is gone for good.
    """
    deleted = await session.scalar(
        delete(db.Page).where(db.Page.id == page_id).returning(db.Page.id)
    )
    if deleted is None:
        raise NotFoundError("Page")
    await session.commit()
    await asyncio.to_thread(delete_page_files, data_dir, [page_id])
