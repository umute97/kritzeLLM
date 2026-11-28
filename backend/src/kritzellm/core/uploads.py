"""Uploads: turning a batch of page photos into new pages, each queued to be read."""

import asyncio
import hashlib
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from kritzellm.db import models as db
from kritzellm.domain import JobKind

from .errors import NotFoundError, PageNumberTakenError
from .images import NormalizedImage, normalize
from .jobs import enqueue, latest_jobs
from .pages import next_page_number, page_number_taken
from .storage import Staging, delete_page_files

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
