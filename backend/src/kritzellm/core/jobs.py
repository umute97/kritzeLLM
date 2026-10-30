"""Background jobs. The `jobs` table is also the queue: the worker claims queued rows in order.

Enqueuing never commits, so a job is only visible (and the worker only woken) together with
whatever the caller commits alongside it. Updates are plain `UPDATE`s, so a job whose page was
deleted meanwhile (and the job with it) just updates nothing.
"""

from collections.abc import Collection
from typing import Any

from sqlalchemy import func, select, update
from sqlalchemy.dialects.postgresql import distinct_on
from sqlalchemy.ext.asyncio import AsyncSession

from kritzellm.api.schemas.jobs import JobKind, JobStatus
from kritzellm.db import models as db

CHANNEL = "kritzellm_jobs"
"""Postgres `NOTIFY` channel that wakes the worker when jobs are queued."""


async def enqueue(session: AsyncSession, kind: JobKind, *, page_id: str | None = None) -> db.Job:
    """Queues a job (on a page, or the whole library) in the session's transaction. The caller commits."""
    job = db.Job(kind=kind, page_id=page_id)
    session.add(job)
    await session.flush()
    # Delivered on commit, and not at all on rollback.
    await session.execute(select(func.pg_notify(CHANNEL, "")))
    return job


async def enqueue_once(
    session: AsyncSession, kind: JobKind, *, page_id: str | None = None
) -> db.Job:
    """The page's (or library's) queued job of this kind, or a newly queued one. The caller commits.

    A queued job hasn't started, so it'll still see whatever changed since it was queued.
    """
    queued = await session.scalar(
        select(db.Job)
        # `== None` is `IS NULL` in SQLAlchemy.
        .where(db.Job.page_id == page_id, db.Job.kind == kind, db.Job.status == JobStatus.QUEUED)
        .limit(1)
    )
    return queued or await enqueue(session, kind, page_id=page_id)


async def pending(session: AsyncSession, page_id: str, kinds: Collection[JobKind]) -> bool:
    """Whether the page has a queued or running job of one of `kinds`."""
    query = select(db.Job.id).where(
        db.Job.page_id == page_id,
        db.Job.kind.in_(kinds),
        db.Job.status.in_((JobStatus.QUEUED, JobStatus.RUNNING)),
    )
    return await session.scalar(query.limit(1)) is not None


async def latest_jobs(session: AsyncSession, page_ids: Collection[str]) -> dict[str, db.Job]:
    """The newest job of each of the pages that has one."""
    if not page_ids:
        return {}
    query = (
        select(db.Job)
        .where(db.Job.page_id.in_(page_ids))
        .ext(distinct_on(db.Job.page_id))
        .order_by(db.Job.page_id, db.Job.id.desc())
    )
    return {job.page_id: job for job in await session.scalars(query) if job.page_id is not None}


async def claim_next(session: AsyncSession) -> db.Job | None:
    """Marks the oldest queued job as running and returns it (`None` if nothing is queued)."""
    oldest = (
        select(db.Job.id)
        .where(db.Job.status == JobStatus.QUEUED)
        .order_by(db.Job.id)
        .limit(1)
        .with_for_update(skip_locked=True)
        .scalar_subquery()
    )
    return await session.scalar(
        update(db.Job)
        .where(db.Job.id == oldest)
        .values(status=JobStatus.RUNNING, started_at=func.now())
        .returning(db.Job)
    )


async def requeue_interrupted(session: AsyncSession) -> int:
    """Puts running jobs back in the queue. Only safe while no worker is running them."""
    requeued = await session.scalars(
        update(db.Job)
        .where(db.Job.status == JobStatus.RUNNING)
        .values(status=JobStatus.QUEUED, started_at=None, progress_done=None, progress_total=None)
        .returning(db.Job.id)
    )
    return len(requeued.all())


async def _update(session: AsyncSession, job_id: str, **values: Any) -> None:
    await session.execute(update(db.Job).where(db.Job.id == job_id).values(**values))


async def set_progress(session: AsyncSession, job_id: str, done: int, total: int) -> None:
    await _update(session, job_id, progress_done=done, progress_total=total)


async def succeed(session: AsyncSession, job_id: str) -> None:
    await _update(session, job_id, status=JobStatus.SUCCEEDED, finished_at=func.now())


async def fail(session: AsyncSession, job_id: str, problem: dict[str, Any]) -> None:
    """Marks the job failed with an RFC 9457 problem."""
    await _update(session, job_id, status=JobStatus.FAILED, error=problem, finished_at=func.now())
