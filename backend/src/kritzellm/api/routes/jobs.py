from typing import Annotated

from fastapi import APIRouter, Query

from kritzellm.core import jobs as core
from kritzellm.core.rows import get_existing
from kritzellm.db import models as db
from kritzellm.domain import JobKind, JobStatus

from ..deps import Session
from ..errors import problem_responses
from ..schemas.jobs import Job, JobList
from .params import JobCursor, JobIdPath, Limit

router = APIRouter(tags=["jobs"], responses=problem_responses(400, 401, 422))


@router.get(
    "/jobs",
    summary="List jobs",
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
    jobs, next_cursor = await core.list_jobs(
        session, status=job_status, kind=kind, limit=limit, cursor=cursor
    )
    return JobList(items=[Job.from_db(job) for job in jobs], next_cursor=next_cursor)


@router.get(
    "/jobs/{jobId}",
    summary="Get a job",
    responses=problem_responses(404),
)
async def get_job(job_id: JobIdPath, session: Session) -> Job:
    """Returns a job's status and progress. Poll this after a `202 Accepted`."""
    return Job.from_db(await get_existing(session, db.Job, job_id))
