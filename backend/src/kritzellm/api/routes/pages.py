import asyncio
from typing import Annotated

from fastapi import APIRouter, Body, Query, Response, status
from fastapi.responses import FileResponse
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import selectinload

from kritzellm.core import pages as core
from kritzellm.core.storage import delete_page_files, variant_path
from kritzellm.db import models as db

from .. import API_PREFIX
from ..deps import AppSettings, Session
from ..errors import http_error, not_found, not_implemented, problem_responses
from ..schemas.blocks import BlocksReplace, BlocksReplaceResult
from ..schemas.common import JournalId, Problem
from ..schemas.jobs import Job
from ..schemas.pages import (
    ImageVariant,
    Page,
    PageDetail,
    PageImage,
    PageImageUrls,
    PageList,
    PageStatus,
    PageUpdate,
    TranscribeRequest,
)
from .blocks import block_out
from .params import BINARY, JOB_LOCATION, DateFrom, DateTo, Limit, PageCursor, PageIdPath

router = APIRouter(tags=["pages"])

IMMUTABLE = "private, max-age=31536000, immutable"
"""A page's images never change, so clients may cache them for good."""


def _image_url(page_id: str, variant: ImageVariant) -> str:
    return f"{API_PREFIX}/pages/{page_id}/image?variant={variant.value}"


def page_out(page: db.Page) -> Page:
    return Page(
        id=page.id,
        journal_id=page.journal_id,
        page_number=page.page_number,
        page_label=page.page_label,
        entry_dates=page.entry_dates,
        status=page.status,
        error=Problem.model_validate(page.error) if page.error else None,
        image=PageImage(
            width=page.width,
            height=page.height,
            urls=PageImageUrls(
                normalized=_image_url(page.id, ImageVariant.NORMALIZED),
                original=_image_url(page.id, ImageVariant.ORIGINAL),
                thumbnail=_image_url(page.id, ImageVariant.THUMBNAIL),
            ),
        ),
        transcription_model=page.transcription_model,
        created_at=page.created_at,
        updated_at=page.updated_at,
    )


async def _get(session: Session, page_id: str) -> db.Page:
    page = await session.get(db.Page, page_id)
    if page is None:
        not_found("Page")
    return page


@router.get(
    "/pages",
    summary="List pages",
    responses=problem_responses(400, 401, 422),
)
async def list_pages(
    session: Session,
    journal_id: Annotated[
        JournalId | None, Query(alias="journalId", description="Only pages of this journal.")
    ] = None,
    page_status: Annotated[
        PageStatus | None, Query(alias="status", description="Only pages in this status.")
    ] = None,
    date_from: DateFrom = None,
    date_to: DateTo = None,
    limit: Limit = 25,
    cursor: PageCursor = None,
) -> PageList:
    """Lists pages: the newest journal's first, each journal's in page-number order.

    The date filters keep pages with at least one entry dated within the range.
    """
    pages, next_cursor = await core.list_pages(
        session,
        journal_id=journal_id,
        status=page_status,
        date_from=date_from,
        date_to=date_to,
        limit=limit,
        cursor=cursor,
    )
    return PageList(items=[page_out(page) for page in pages], next_cursor=next_cursor)


@router.get(
    "/pages/{pageId}",
    summary="Get a page",
    responses=problem_responses(400, 401, 404, 422),
)
async def get_page(page_id: PageIdPath, session: Session) -> PageDetail:
    """Returns a page with all of its transcribed blocks, in reading order."""
    page = await session.get(db.Page, page_id, options=[selectinload(db.Page.blocks)])
    if page is None:
        not_found("Page")
    return PageDetail(**dict(page_out(page)), blocks=[block_out(block) for block in page.blocks])


@router.patch(
    "/pages/{pageId}",
    summary="Update a page",
    responses=problem_responses(400, 401, 404, 409, 422),
)
async def update_page(page_id: PageIdPath, body: PageUpdate, session: Session) -> Page:
    """Corrects page metadata (number, label, dates) or moves the page to another journal.

    Changing dates or the journal re-indexes the page.
    """
    page = await _get(session, page_id)
    changes = body.model_dump(exclude_unset=True, by_alias=False)

    journal_id = changes.get("journal_id", page.journal_id)
    if journal_id != page.journal_id:
        if await session.get(db.Journal, journal_id) is None:
            not_found("Journal")
        twin = select(db.Page.id).where(
            db.Page.journal_id == journal_id, db.Page.sha256 == page.sha256
        )
        if await session.scalar(twin) is not None:
            http_error(409, "That journal already has a page with this image.")
        changes.setdefault("page_number", await core.next_page_number(session, journal_id))
    if (number := changes.get("page_number")) is not None and await core.page_number_taken(
        session, journal_id, number, number, besides=page.id
    ):
        http_error(409, f"Page number {number} is taken in that journal.")
    if "entry_dates" in changes:
        changes["entry_dates"] = sorted(set(changes["entry_dates"]))

    for field, value in changes.items():
        setattr(page, field, value)
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        http_error(409, "Another change to that journal got in first. Please try again.")
    await session.refresh(page)
    return page_out(page)


@router.delete(
    "/pages/{pageId}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    summary="Delete a page",
    responses=problem_responses(400, 401, 404, 422),
)
async def delete_page(page_id: PageIdPath, session: Session, settings: AppSettings) -> None:
    """Deletes a page, its images, blocks and search index entries. This can't be undone."""
    deleted = await session.scalar(
        delete(db.Page).where(db.Page.id == page_id).returning(db.Page.id)
    )
    if deleted is None:
        not_found("Page")
    await session.commit()
    await asyncio.to_thread(delete_page_files, settings.data_dir, [page_id])


@router.get(
    "/pages/{pageId}/image",
    response_class=Response,
    summary="Get a page image",
    responses={
        200: {
            "description": "The image bytes.",
            "content": {
                "image/jpeg": BINARY,
                "image/png": BINARY,
                "image/heic": BINARY,
                "image/heif": BINARY,
                "image/webp": BINARY,
            },
        },
        **problem_responses(400, 401, 404, 422),
    },
)
async def get_page_image(
    page_id: PageIdPath,
    session: Session,
    settings: AppSettings,
    variant: Annotated[
        ImageVariant, Query(description="Which version of the image to return.")
    ] = ImageVariant.NORMALIZED,
) -> Response:
    """Returns the page image.

    `normalized` (the default) is the rotated, resized JPEG that gets transcribed.
    `original` is the uploaded file as-is, and `thumbnail` is a small JPEG preview. A page's images
    never change, so they may be cached for good.
    """
    page = await _get(session, page_id)
    path = variant_path(settings.data_dir, page.id, variant, page.original_media_type)
    if not await asyncio.to_thread(path.is_file):
        not_found("Image file")
    media_type = page.original_media_type if variant is ImageVariant.ORIGINAL else "image/jpeg"
    return FileResponse(path, media_type=media_type, headers={"Cache-Control": IMMUTABLE})


@router.put(
    "/pages/{pageId}/blocks",
    summary="Replace a page's blocks",
    tags=["blocks"],
    responses=problem_responses(400, 401, 404, 409, 422),
)
async def replace_page_blocks(page_id: PageIdPath, body: BlocksReplace) -> BlocksReplaceResult:
    """Replaces the whole transcription of a page, in reading order.

    Blocks sent with an `id` are updated in place (so existing chat sources keep working); blocks
    without one are created; existing blocks that aren't sent are deleted. The page is re-indexed in
    the background.
    """
    not_implemented()


@router.post(
    "/pages/{pageId}/transcribe",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Re-transcribe a page",
    responses={202: {"headers": JOB_LOCATION}, **problem_responses(400, 401, 404, 409, 422)},
)
async def transcribe_page(
    page_id: PageIdPath, body: Annotated[TranscribeRequest | None, Body()] = None
) -> Job:
    """Throws away the current blocks and reads the page again, optionally with another model.

    Manual edits are lost.
    """
    not_implemented()
