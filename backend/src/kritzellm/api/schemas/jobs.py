"""Background jobs."""

from enum import StrEnum
from typing import TYPE_CHECKING, Self

from pydantic import Field

from kritzellm.domain import JobKind, JobStatus

from .common import ApiModel, JobId, PageId, Problem, Timestamp

if TYPE_CHECKING:
    from kritzellm.db import models as db


class JobTargetType(StrEnum):
    """Kind of thing a job works on."""

    PAGE = "page"


class JobTarget(ApiModel):
    """What the job works on."""

    type: JobTargetType
    id: PageId


class JobProgress(ApiModel):
    """How far along a job is."""

    done: int = Field(ge=0)
    """Units finished so far."""
    total: int = Field(ge=0)
    """Total units of work."""


class Job(ApiModel):
    """A unit of background work. Poll it until `status` is `succeeded` or `failed`."""

    id: JobId
    kind: JobKind
    status: JobStatus
    target: JobTarget | None
    """What the job works on; `null` for jobs over the whole library (`reindexAll`)."""
    progress: JobProgress | None
    """How far along the job is, when it can tell."""
    error: Problem | None
    """Why the job failed; `null` unless `status` is `failed`."""
    created_at: Timestamp
    started_at: Timestamp | None
    """When a worker picked the job up."""
    finished_at: Timestamp | None
    """When the job succeeded or failed."""

    @classmethod
    def from_db(cls, job: db.Job) -> Self:
        """The API view of a stored job."""
        progress = target = None
        if job.progress_done is not None and job.progress_total is not None:
            progress = {"done": job.progress_done, "total": job.progress_total}
        if job.page_id is not None:
            target = {"type": JobTargetType.PAGE, "id": job.page_id}
        return cls.from_row(job, progress=progress, target=target)


class JobList(ApiModel):
    """A page of jobs."""

    items: list[Job]
    next_cursor: JobId | None
    """Pass as `cursor` to get the next page; `null` on the last page."""
