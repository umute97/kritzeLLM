from typing import Annotated

from fastapi import APIRouter, Query, Response, status
from sqlalchemy import select

from kritzellm.db import models as db

from ..deps import Session
from ..errors import not_found, not_implemented, problem_responses
from ..pagination import paginate
from ..schemas.common import Problem
from ..schemas.jobs import (
    Job,
    JobKind,
    JobList,
    JobProgress,
    JobStatus,
    JobTarget,
    JobTargetType,
)
from .params import BINARY, JOB_LOCATION, JobCursor, JobIdPath, Limit

router = APIRouter()


def job_out(job: db.Job) -> Job:
    if job.page_id is not None:
        target = JobTarget(type=JobTargetType.PAGE, id=job.page_id)
    elif job.journal_id is not None:
        target = JobTarget(type=JobTargetType.JOURNAL, id=job.journal_id)
    else:
        target = JobTarget(type=JobTargetType.ALL, id=None)
    progress = None
    if job.progress_done is not None and job.progress_total is not None:
        progress = JobProgress(done=job.progress_done, total=job.progress_total)
    return Job(
        id=job.id,
        kind=job.kind,
        status=job.status,
        target=target,
        progress=progress,
        result_url=None,
        error=Problem.model_validate(job.error) if job.error else None,
        created_at=job.created_at,
        started_at=job.started_at,
        finished_at=job.finished_at,
    )


@router.get(
    "/jobs",
    summary="List jobs",
    tags=["jobs"],
    responses=problem_responses(400, 401, 422),
)
async def list_jobs(
    session: Session,
    job_status: Annotated[
        JobStatus | None, Query(alias="status", description="Only jobs in this status.")
    ] = None,
    kind: Annotated[JobKind | None, Query(description="Only jobs of this kind.")] = None,
    limit: Limit = 25,
    cursor: JobCursor = None,
) -> JobList:
    """Lists background jobs, newest first."""
    query = select(db.Job)
    if job_status is not None:
        query = query.where(db.Job.status == job_status)
    if kind is not None:
        query = query.where(db.Job.kind == kind)
    rows, next_cursor = await paginate(
        session, query, id_column=db.Job.id, limit=limit, cursor=cursor
    )
    return JobList(items=[job_out(job) for (job,) in rows], next_cursor=next_cursor)


@router.get(
    "/jobs/{jobId}",
    summary="Get a job",
    tags=["jobs"],
    responses=problem_responses(400, 401, 404, 422),
)
async def get_job(job_id: JobIdPath, session: Session) -> Job:
    """Returns a job's status and progress. Poll this after a `202 Accepted`."""
    job = await session.get(db.Job, job_id)
    if job is None:
        not_found("Job")
    return job_out(job)


@router.get(
    "/jobs/{jobId}/result",
    response_class=Response,
    summary="Download a job's result",
    tags=["jobs"],
    responses={
        200: {
            "description": "The result file, with a `Content-Disposition` filename.",
            "content": {"application/zip": BINARY},
        },
        **problem_responses(400, 401, 404, 409, 422),
    },
)
async def get_job_result(job_id: JobIdPath) -> Response:
    """Downloads the file a finished job produced (currently only exports).

    Returns `409` while the job hasn't succeeded.
    """
    not_implemented()


@router.post(
    "/admin/reindex",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Re-index everything",
    tags=["admin"],
    responses={202: {"headers": JOB_LOCATION}, **problem_responses(400, 401, 409)},
)
async def reindex_all() -> Job:
    """Rebuilds the search index for all pages, e.g. after switching the embedding model.

    Transcriptions are kept.
    """
    not_implemented()
