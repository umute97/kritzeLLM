import asyncio
import hashlib
from typing import Annotated

from fastapi import APIRouter, File, Form, Request, Response, UploadFile, status
from pydantic import WithJsonSchema
from sqlalchemy import delete, func, select

from kritzellm.core.images import (
    ImageTooLargeError,
    NormalizedImage,
    UnsupportedImageError,
    normalize,
)
from kritzellm.core.pages import (
    JournalNotFoundError,
    PageNumberTakenError,
    StagedUpload,
    add_pages,
)
from kritzellm.core.storage import Staging, delete_page_files
from kritzellm.db import models as db

from ..deps import AppSettings, Session
from ..errors import http_error, not_found, not_implemented, problem_responses
from ..pagination import paginate
from ..schemas.jobs import Job
from ..schemas.journals import ExportCreate, Journal, JournalCreate, JournalList, JournalUpdate
from ..schemas.pages import MAX_PAGE_NUMBER, UploadItem, UploadResult
from .pages import page_out
from .params import JOB_LOCATION, JournalCursor, JournalIdPath, Limit, location_header

router = APIRouter(tags=["journals"])

MAX_FILE_BYTES = 25 * 1024 * 1024
MAX_FILES = 100

PAGE_COUNT = (
    select(func.count(db.Page.id))
    .where(db.Page.journal_id == db.Journal.id)
    .correlate(db.Journal)
    .scalar_subquery()
)


def _journal_out(journal: db.Journal, page_count: int) -> Journal:
    return Journal(
        id=journal.id,
        name=journal.name,
        description=journal.description,
        page_count=page_count,
        created_at=journal.created_at,
        updated_at=journal.updated_at,
    )


async def _get(session: Session, journal_id: str) -> Journal:
    row = (
        await session.execute(select(db.Journal, PAGE_COUNT).where(db.Journal.id == journal_id))
    ).one_or_none()
    if row is None:
        not_found("Journal")
    return _journal_out(*row)


@router.get(
    "/journals",
    summary="List journals",
    responses=problem_responses(400, 401, 422),
)
async def list_journals(
    session: Session, limit: Limit = 25, cursor: JournalCursor = None
) -> JournalList:
    """Lists all journals, newest first."""
    rows, next_cursor = await paginate(
        session,
        select(db.Journal, PAGE_COUNT),
        id_column=db.Journal.id,
        limit=limit,
        cursor=cursor,
    )
    return JournalList(items=[_journal_out(*row) for row in rows], next_cursor=next_cursor)


@router.post(
    "/journals",
    status_code=status.HTTP_201_CREATED,
    summary="Create a journal",
    responses={
        201: {"headers": location_header("URL of the new journal.")},
        **problem_responses(400, 401, 422),
    },
)
async def create_journal(
    body: JournalCreate, session: Session, request: Request, response: Response
) -> Journal:
    """Creates an empty journal to upload pages into."""
    journal = db.Journal(**body.model_dump(by_alias=False))
    session.add(journal)
    await session.commit()
    await session.refresh(journal)
    response.headers["Location"] = request.url_for("get_journal", journalId=journal.id).path
    return _journal_out(journal, page_count=0)


@router.get(
    "/journals/{journalId}",
    summary="Get a journal",
    responses=problem_responses(400, 401, 404, 422),
)
async def get_journal(journal_id: JournalIdPath, session: Session) -> Journal:
    """Returns a single journal."""
    return await _get(session, journal_id)


@router.patch(
    "/journals/{journalId}",
    summary="Update a journal",
    responses=problem_responses(400, 401, 404, 422),
)
async def update_journal(
    journal_id: JournalIdPath, body: JournalUpdate, session: Session
) -> Journal:
    """Renames a journal or changes its description. Only the given fields change."""
    journal = await session.get(db.Journal, journal_id)
    if journal is None:
        not_found("Journal")
    for field, value in body.model_dump(exclude_unset=True, by_alias=False).items():
        setattr(journal, field, value)
    await session.commit()
    return await _get(session, journal_id)


@router.delete(
    "/journals/{journalId}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    summary="Delete a journal",
    responses=problem_responses(400, 401, 404, 422),
)
async def delete_journal(
    journal_id: JournalIdPath, session: Session, settings: AppSettings
) -> None:
    """Deletes a journal with all of its pages, images, blocks and search index entries.

    This can't be undone.
    """
    # Locks the journal, so no pages can be added to it before it's gone.
    deleted = await session.scalar(
        select(db.Journal.id).where(db.Journal.id == journal_id).with_for_update()
    )
    if deleted is None:
        not_found("Journal")
    page_ids = (
        await session.scalars(select(db.Page.id).where(db.Page.journal_id == journal_id))
    ).all()
    await session.execute(delete(db.Journal).where(db.Journal.id == journal_id))
    await session.commit()
    await asyncio.to_thread(delete_page_files, settings.data_dir, page_ids)


def _hash_and_normalize(data: bytes) -> tuple[bytes, NormalizedImage]:
    return hashlib.sha256(data).digest(), normalize(data)


async def _stage(file: UploadFile, staging: Staging) -> StagedUpload:
    """Checks one uploaded file and stages its images. Raises a `413` or `415` for bad files."""
    filename = (file.filename or "").replace("\x00", "")[:255]
    too_big = f"{filename or 'A file'} is bigger than 25 MB."
    if file.size is not None and file.size > MAX_FILE_BYTES:
        http_error(413, too_big)
    data = await file.read(MAX_FILE_BYTES + 1)
    if len(data) > MAX_FILE_BYTES:
        http_error(413, too_big)
    try:
        sha256, image = await asyncio.to_thread(_hash_and_normalize, data)
    except UnsupportedImageError as exc:
        http_error(415, f"{filename or 'A file'}: {exc} Use JPEG, PNG, HEIC/HEIF or WebP.")
    except ImageTooLargeError as exc:
        http_error(413, f"{filename or 'A file'}: {exc}")
    folder = await asyncio.to_thread(staging.stage, data, image)
    return StagedUpload(
        filename=filename,
        sha256=sha256,
        media_type=image.media_type,
        width=image.width,
        height=image.height,
        folder=folder,
    )


@router.post(
    "/journals/{journalId}/pages",
    status_code=status.HTTP_201_CREATED,
    summary="Upload pages",
    tags=["pages"],
    responses=problem_responses(400, 401, 404, 409, 413, 415, 422),
)
async def upload_pages(
    journal_id: JournalIdPath,
    session: Session,
    settings: AppSettings,
    files: Annotated[
        list[UploadFile],
        File(
            min_length=1,
            max_length=MAX_FILES,
            description=(
                f"Page images in page order: JPEG, PNG, HEIC/HEIF or WebP, up to 25 MB each "
                f"and {MAX_FILES} per upload."
            ),
        ),
    ],
    start_page_number: Annotated[
        int | None,
        # Multipart has no `null`: leave the field out instead.
        WithJsonSchema({"type": "integer", "minimum": 1, "maximum": MAX_PAGE_NUMBER}),
        Form(
            alias="startPageNumber",
            ge=1,
            le=MAX_PAGE_NUMBER,
            description=(
                "Page number for the first new page; the rest count up from it. "
                "Defaults to the journal's next free page number."
            ),
        ),
    ] = None,
) -> UploadResult:
    """Uploads page photos or scans into a journal.

    Each file is turned upright and stored with a normalized JPEG and a thumbnail, then becomes a
    page that's transcribed and indexed in the background. If any file isn't a supported image or
    is too big, nothing is stored.

    Uploads are idempotent per file: a file whose SHA-256 is already in this journal (or earlier
    in the same upload) returns the existing page with `duplicate: true` and takes no page number,
    so a failed upload can simply be sent again.
    """
    if await session.get(db.Journal, journal_id) is None:
        not_found("Journal")
    async with Staging(settings.data_dir) as staging:
        uploads = [await _stage(file, staging) for file in files]
        try:
            added = await add_pages(
                session, staging, journal_id, uploads, start_page_number=start_page_number
            )
        except PageNumberTakenError:
            http_error(409, "Some of the page numbers for the new pages are taken in this journal.")
        except JournalNotFoundError:
            not_found("Journal")
    return UploadResult(
        items=[
            UploadItem(
                filename=item.filename, page=page_out(item.page), duplicate=item.duplicate, job=None
            )
            for item in added
        ]
    )


@router.post(
    "/journals/{journalId}/exports",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Export a journal",
    responses={202: {"headers": JOB_LOCATION}, **problem_responses(400, 401, 404, 422)},
)
async def export_journal(journal_id: JournalIdPath, body: ExportCreate) -> Job:
    """Starts a zipped export of all pages and transcriptions.

    When the job succeeds, download the file from its `resultUrl`.
    """
    not_implemented()
