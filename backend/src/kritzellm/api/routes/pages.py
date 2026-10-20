import asyncio
from typing import Annotated

from fastapi import APIRouter, Query, Request, Response, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse
from sqlalchemy.orm import selectinload

from kritzellm.core import blocks as core_blocks
from kritzellm.core import pages as core
from kritzellm.core.errors import NotFoundError, get_existing
from kritzellm.core.storage import variant_path
from kritzellm.db import models as db

from .. import API_PREFIX
from ..deps import AppSettings, Session
from ..errors import problem_responses
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
)
from .blocks import block_out
from .jobs import job_out
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
    page = await get_existing(session, db.Page, page_id, options=[selectinload(db.Page.blocks)])
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
    changes = body.model_dump(exclude_unset=True, by_alias=False)
    return page_out(await core.update_page(session, page_id, changes))


@router.delete(
    "/pages/{pageId}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    summary="Delete a page",
    responses=problem_responses(400, 401, 404, 422),
)
async def delete_page(page_id: PageIdPath, session: Session, settings: AppSettings) -> None:
    """Deletes a page, its images, blocks and search index entries. This can't be undone."""
    await core.delete_page(session, settings.data_dir, page_id)


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
    page = await get_existing(session, db.Page, page_id)
    path = variant_path(settings.data_dir, page.id, variant, page.original_media_type)
    if not await asyncio.to_thread(path.is_file):
        raise NotFoundError("Image file")
    media_type = page.original_media_type if variant is ImageVariant.ORIGINAL else "image/jpeg"
    return FileResponse(path, media_type=media_type, headers={"Cache-Control": IMMUTABLE})


@router.put(
    "/pages/{pageId}/blocks",
    summary="Replace a page's blocks",
    tags=["blocks"],
    responses=problem_responses(400, 401, 404, 409, 422),
)
async def replace_page_blocks(
    page_id: PageIdPath, body: BlocksReplace, session: Session
) -> BlocksReplaceResult:
    """Replaces the whole transcription of a page, in reading order.

    Blocks sent with an `id` are updated in place (so existing chat sources keep working); blocks
    without one are created; existing blocks that aren't sent are deleted. The page is re-indexed in
    the background. Returns `409` while the page is waiting to be read or being read.
    """
    try:
        blocks, job = await core_blocks.replace_blocks(session, page_id, body.blocks)
    except core_blocks.BlockIdError as exc:
        errors = [
            {"type": "value_error", "loc": ("body", "blocks", index, "id"), "msg": message}
            for index, message in exc.problems
        ]
        raise RequestValidationError(errors) from None
    await session.commit()
    return BlocksReplaceResult(blocks=[block_out(block) for block in blocks], job=job_out(job))


@router.post(
    "/pages/{pageId}/transcribe",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Re-transcribe a page",
    responses={202: {"headers": JOB_LOCATION}, **problem_responses(400, 401, 404, 409, 422)},
)
async def transcribe_page(
    page_id: PageIdPath, session: Session, request: Request, response: Response
) -> Job:
    """Throws away the current blocks and reads the page again.

    Manual edits are lost. Returns `409` while the page is already waiting to be read or being read.
    """
    job = await core_blocks.request_transcription(session, page_id)
    await session.commit()
    response.headers["Location"] = request.url_for("get_job", jobId=job.id).path
    return job_out(job)
