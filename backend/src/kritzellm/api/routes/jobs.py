from typing import Annotated

from fastapi import APIRouter, Query
from sqlalchemy import select

from kritzellm.core.errors import get_existing
from kritzellm.core.pagination import paginate
from kritzellm.db import models as db

from ..deps import Session
from ..errors import problem_responses
from ..schemas.jobs import (
    Job,
    JobKind,
    JobList,
    JobStatus,
)
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
    query = select(db.Job)
    if job_status is not None:
        query = query.where(db.Job.status == job_status)
    if kind is not None:
        query = query.where(db.Job.kind == kind)
    rows, next_cursor = await paginate(
        session, query, id_column=db.Job.id, limit=limit, cursor=cursor
    )
    return JobList(items=[Job.from_db(job) for (job,) in rows], next_cursor=next_cursor)


@router.get(
    "/jobs/{jobId}",
    summary="Get a job",
    responses=problem_responses(404),
)
async def get_job(job_id: JobIdPath, session: Session) -> Job:
    """Returns a job's status and progress. Poll this after a `202 Accepted`."""
    return Job.from_db(await get_existing(session, db.Job, job_id))
