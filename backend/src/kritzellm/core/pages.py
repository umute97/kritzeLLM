"""Pages: listing, adding, correcting and deleting them, tracking their processing, saving their text."""

import asyncio
import hashlib
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

from sqlalchemy import and_, delete, func, or_, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from kritzellm.api.schemas.jobs import JobKind
from kritzellm.api.schemas.pages import PAGE_CURSOR, PageStatus
from kritzellm.db import models as db

from .errors import ConflictError, NotFoundError, PageNumberTakenError, get_existing
from .images import NormalizedImage, normalize
from .jobs import enqueue, latest_jobs
from .storage import Staging, delete_page_files
from .transcribe import PageTranscription


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


PAGE_NUMBERS_TAKEN = "Some of the page numbers for the new pages are taken in this journal."


@dataclass(frozen=True, slots=True)
class StagedUpload:
    """An uploaded file whose images are staged and ready to become a page."""

    filename: str
    sha256: bytes
    media_type: str
    width: int
    height: int
    folder: Path


def _hash_and_normalize(data: bytes) -> tuple[bytes, NormalizedImage]:
    return hashlib.sha256(data).digest(), normalize(data)


async def stage_upload(staging: Staging, filename: str, data: bytes) -> StagedUpload:
    """Checks an uploaded file and stages its images, ready for `add_pages`.

    Raises `UnsupportedImageError` or `ImageTooLargeError` for files that aren't usable images.
    """
    sha256, image = await asyncio.to_thread(_hash_and_normalize, data)
    folder = await asyncio.to_thread(staging.stage, data, image)
    return StagedUpload(
        filename=filename,
        sha256=sha256,
        media_type=image.media_type,
        width=image.width,
        height=image.height,
        folder=folder,
    )


@dataclass(frozen=True, slots=True)
class AddedPage:
    filename: str
    page: db.Page
    duplicate: bool
    """The file was already in the journal (or earlier in the same upload)."""
    job: db.Job | None
    """The page's newest job: the new ingest job, or for a duplicate whatever ran last."""


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
                raise PageNumberTakenError(PAGE_NUMBERS_TAKEN) from exc
            if "fk_pages_journal_id_journals" in message:
                raise NotFoundError("Journal") from exc  # Deleted while the pages were added.
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
    jobs = await latest_jobs(session, [page.id for page in pages.values()])

    number = start_page_number or await next_page_number(session, journal_id)
    new_count = len(hashes - pages.keys())
    if (
        start_page_number is not None
        and new_count
        and await page_number_taken(session, journal_id, number, number + new_count - 1)
    ):
        raise PageNumberTakenError(PAGE_NUMBERS_TAKEN)

    outcomes, new = [], []
    for upload in uploads:
        if (page := pages.get(upload.sha256)) is not None:
            outcomes.append((upload.filename, page, True))
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
        outcomes.append((upload.filename, page, False))
    session.add_all(page for page, _ in new)
    # Duplicate files surface here, before anything is moved, so `add_pages` can retry.
    await session.flush()

    # Pages, their files and their jobs appear together: the worker may start right on commit.
    published = []
    try:
        for page, upload in new:
            await asyncio.to_thread(staging.publish, upload.folder, page.id)
            published.append(page.id)
        for page, _ in new:
            jobs[page.id] = await enqueue(session, JobKind.INGEST_PAGE, page_id=page.id)
        await session.commit()
    except BaseException:
        await asyncio.to_thread(delete_page_files, staging.data_dir, published)
        raise
    return [
        AddedPage(filename, page, duplicate, jobs.get(page.id))
        for filename, page, duplicate in outcomes
    ]


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
        page.entry_dates = sorted(set(transcription.entry_dates))
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
    if "entry_dates" in changes:
        changes["entry_dates"] = sorted(set(changes["entry_dates"]))

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
