from contextlib import aclosing
from typing import Annotated

from fastapi import APIRouter, File, Form, Request, Response, UploadFile, status
from pydantic import WithJsonSchema

from kritzellm.core import journals as core
from kritzellm.core.errors import get_existing
from kritzellm.core.images import ImageTooLargeError, UnsupportedImageError
from kritzellm.core.pages import StagedUpload, add_pages, stage_upload
from kritzellm.core.storage import Staging
from kritzellm.db import models as db

from ..deps import AppSettings, Session
from ..errors import http_error, problem_responses
from ..schemas.jobs import Job
from ..schemas.journals import Journal, JournalCreate, JournalList, JournalUpdate
from ..schemas.pages import MAX_PAGE_NUMBER, Page, UploadItem, UploadResult
from .params import JournalCursor, JournalIdPath, Limit, location_header

router = APIRouter(tags=["journals"], responses=problem_responses(400, 401, 422))

MAX_FILE_BYTES = 25 * 1024 * 1024
MAX_FILES = 100


@router.get(
    "/journals",
    summary="List journals",
)
async def list_journals(
    session: Session, limit: Limit = 25, cursor: JournalCursor = None
) -> JournalList:
    """Lists all journals, newest first."""
    journals, next_cursor = await core.list_journals(session, limit=limit, cursor=cursor)
    return JournalList(
        items=[Journal.model_validate(journal) for journal in journals], next_cursor=next_cursor
    )


@router.post(
    "/journals",
    status_code=status.HTTP_201_CREATED,
    summary="Create a journal",
    responses={
        201: {"headers": location_header("URL of the new journal.")},
    },
)
async def create_journal(
    body: JournalCreate, session: Session, request: Request, response: Response
) -> Journal:
    """Creates an empty journal to upload pages into."""
    journal = await core.create_journal(session, **body.model_dump(by_alias=False))
    await session.commit()
    response.headers["Location"] = request.url_for("get_journal", journalId=journal.id).path
    return Journal.model_validate(journal)


@router.get(
    "/journals/{journalId}",
    summary="Get a journal",
    responses=problem_responses(404),
)
async def get_journal(journal_id: JournalIdPath, session: Session) -> Journal:
    """Returns a single journal."""
    return Journal.model_validate(await get_existing(session, db.Journal, journal_id))


@router.patch(
    "/journals/{journalId}",
    summary="Update a journal",
    responses=problem_responses(404),
)
async def update_journal(
    journal_id: JournalIdPath, body: JournalUpdate, session: Session
) -> Journal:
    """Renames a journal or changes its description. Only the given fields change."""
    changes = body.model_dump(exclude_unset=True, by_alias=False)
    journal = await core.update_journal(session, journal_id, changes)
    await session.commit()
    return Journal.model_validate(journal)


@router.delete(
    "/journals/{journalId}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    summary="Delete a journal",
    responses=problem_responses(404),
)
async def delete_journal(
    journal_id: JournalIdPath, session: Session, settings: AppSettings
) -> None:
    """Deletes a journal with all of its pages, images, blocks and search index entries.

    This can't be undone.
    """
    await core.delete_journal(session, settings.data_dir, journal_id)


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
        return await stage_upload(staging, filename, data)
    except UnsupportedImageError as exc:
        http_error(415, f"{filename or 'A file'}: {exc} Use JPEG, PNG, HEIC/HEIF or WebP.")
    except ImageTooLargeError as exc:
        http_error(413, f"{filename or 'A file'}: {exc}")


@router.post(
    "/journals/{journalId}/pages",
    status_code=status.HTTP_201_CREATED,
    summary="Upload pages",
    tags=["pages"],
    responses=problem_responses(404, 409, 413, 415),
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
    await get_existing(session, db.Journal, journal_id)
    async with aclosing(Staging(settings.data_dir)) as staging:
        uploads = [await _stage(file, staging) for file in files]
        added = await add_pages(
            session, staging, journal_id, uploads, start_page_number=start_page_number
        )
    return UploadResult(
        items=[
            UploadItem(
                filename=item.filename,
                page=Page.from_db(item.page),
                duplicate=item.duplicate,
                job=Job.from_db(item.job) if item.job else None,
            )
            for item in added
        ]
    )
