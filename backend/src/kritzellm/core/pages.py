"""Pages: listing them and adding uploaded ones."""

import asyncio
import re
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from sqlalchemy import and_, delete, func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from kritzellm.api.schemas.pages import PAGE_CURSOR, PageStatus
from kritzellm.db import models as db

from .storage import Staging, delete_page_files


class PageNumberTakenError(Exception):
    """Another page of the journal already has the page number."""


class JournalNotFoundError(Exception):
    """The journal was deleted while pages were being added to it."""


def encode_cursor(page: db.Page) -> str:
    """A cursor for the position right after `page`."""
    return f"{page.journal_id}.{page.page_number}"


def decode_cursor(cursor: str) -> tuple[str, int]:
    """The journal ID and page number in a cursor. Raises `ValueError` if it isn't one."""
    if not re.fullmatch(PAGE_CURSOR, cursor):
        raise ValueError("Not a page cursor")
    journal_id, _, number = cursor.partition(".")
    return journal_id, int(number)


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
        day = func.unnest(db.Page.entry_dates).column_valued()
        in_range = select(day)
        if date_from is not None:
            in_range = in_range.where(day >= date_from)
        if date_to is not None:
            in_range = in_range.where(day <= date_to)
        query = query.where(in_range.exists())
    if cursor is not None:
        after_journal, after_number = decode_cursor(cursor)
        query = query.where(
            or_(
                db.Page.journal_id < after_journal,
                and_(db.Page.journal_id == after_journal, db.Page.page_number > after_number),
            )
        )
    query = query.order_by(db.Page.journal_id.desc(), db.Page.page_number).limit(limit + 1)
    pages = list((await session.scalars(query)).all())
    if len(pages) <= limit:
        return pages, None
    return pages[:limit], encode_cursor(pages[limit - 1])


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


@dataclass(frozen=True, slots=True)
class StagedUpload:
    """An uploaded file whose images are staged and ready to become a page."""

    filename: str
    sha256: bytes
    media_type: str
    width: int
    height: int
    folder: Path


@dataclass(frozen=True, slots=True)
class AddedPage:
    filename: str
    page: db.Page
    duplicate: bool
    """The file was already in the journal (or earlier in the same upload)."""


async def add_pages(
    session: AsyncSession,
    staging: Staging,
    journal_id: str,
    uploads: Sequence[StagedUpload],
    *,
    start_page_number: int | None = None,
) -> list[AddedPage]:
    """Turns staged uploads into pages, in order, skipping files the journal already has.

    New pages are numbered consecutively from `start_page_number` (default: the next free number).
    Raises `PageNumberTakenError` if one of those numbers is taken.
    """
    for attempt in range(2):
        try:
            return await _add_pages(session, staging, journal_id, uploads, start_page_number)
        except IntegrityError as exc:
            await session.rollback()
            message = str(exc.orig)
            if "uq_pages_journal_id_page_number" in message:
                raise PageNumberTakenError from exc
            if "fk_pages_journal_id_journals" in message:
                raise JournalNotFoundError from exc
            # Another upload added some of the same files meanwhile: once more, as duplicates.
            if "uq_pages_journal_id_sha256" not in message or attempt:
                raise
    raise AssertionError("unreachable")


async def _add_pages(
    session: AsyncSession,
    staging: Staging,
    journal_id: str,
    uploads: Sequence[StagedUpload],
    start_page_number: int | None,
) -> list[AddedPage]:
    hashes = {upload.sha256 for upload in uploads}
    known = await session.scalars(
        select(db.Page).where(db.Page.journal_id == journal_id, db.Page.sha256.in_(hashes))
    )
    pages = {page.sha256: page for page in known}

    number = start_page_number or await next_page_number(session, journal_id)
    new_count = len(hashes - pages.keys())
    if (
        start_page_number is not None
        and new_count
        and await page_number_taken(session, journal_id, number, number + new_count - 1)
    ):
        raise PageNumberTakenError

    added, new = [], []
    for upload in uploads:
        if (page := pages.get(upload.sha256)) is not None:
            added.append(AddedPage(upload.filename, page, duplicate=True))
            continue
        page = db.Page(
            journal_id=journal_id,
            page_number=number,
            original_filename=upload.filename,
            original_media_type=upload.media_type,
            sha256=upload.sha256,
            width=upload.width,
            height=upload.height,
        )
        number += 1
        pages[upload.sha256] = page
        new.append((page, upload))
        added.append(AddedPage(upload.filename, page, duplicate=False))
    session.add_all(page for page, _ in new)
    await session.commit()

    published = []
    try:
        for page, upload in new:
            await asyncio.to_thread(staging.publish, upload.folder, page.id)
            published.append(page.id)
    except BaseException:
        new_ids = [page.id for page, _ in new]
        await session.execute(delete(db.Page).where(db.Page.id.in_(new_ids)))
        await session.commit()
        await asyncio.to_thread(delete_page_files, staging.data_dir, published)
        raise
    return added
