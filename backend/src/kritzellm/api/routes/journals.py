from typing import Annotated

from fastapi import APIRouter, File, Form, Header, Request, Response, UploadFile, status
from sqlalchemy import delete, func, select

from kritzellm.db import models as db

from ..deps import Session
from ..errors import not_found, not_implemented, problem_responses
from ..pagination import paginate
from ..schemas.jobs import Job
from ..schemas.journals import ExportCreate, Journal, JournalCreate, JournalList, JournalUpdate
from ..schemas.pages import UploadResult
from .params import JOB_LOCATION, JournalCursor, JournalIdPath, Limit, location_header

router = APIRouter(tags=["journals"])

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
    journal = db.Journal(**body.model_dump())
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
    for field, value in body.model_dump(exclude_unset=True).items():
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
async def delete_journal(journal_id: JournalIdPath, session: Session) -> None:
    """Deletes a journal with all of its pages, images, blocks and search index entries.

    This can't be undone.
    """
    deleted = await session.scalar(
        delete(db.Journal).where(db.Journal.id == journal_id).returning(db.Journal.id)
    )
    if deleted is None:
        not_found("Journal")
    await session.commit()


@router.post(
    "/journals/{journalId}/pages",
    status_code=status.HTTP_201_CREATED,
    summary="Upload pages",
    tags=["pages"],
    responses=problem_responses(400, 401, 404, 413, 415, 422),
)
async def upload_pages(
    journal_id: JournalIdPath,
    files: Annotated[
        list[UploadFile],
        File(
            description="Page images in page order. JPEG, PNG, HEIC/HEIF or WebP, up to 25 MB each.",
        ),
    ],
    start_page_number: Annotated[
        int | None,
        Form(
            alias="startPageNumber",
            ge=1,
            description=(
                "Page number for the first file; the rest count up from it. "
                "Defaults to the journal's next free page number."
            ),
        ),
    ] = None,
    idempotency_key: Annotated[
        str | None,
        Header(
            alias="Idempotency-Key",
            min_length=1,
            max_length=255,
            description="Any unique string (e.g. a UUID). Retries with the same key return the first response.",
        ),
    ] = None,
) -> UploadResult:
    """Uploads page photos or scans into a journal.

    Each new page gets an `ingestPage` job that normalizes the image, transcribes it and indexes it.

    Uploads are idempotent per file: a file whose SHA-256 already exists in this journal returns the
    existing page with `duplicate: true` and no new job. Sending the same `Idempotency-Key` again
    replays the original response.
    """
    not_implemented()


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
