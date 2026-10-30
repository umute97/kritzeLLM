from fastapi import APIRouter, Request, Response, status

from kritzellm.core import jobs

from ..deps import Session
from ..errors import problem_responses
from ..schemas.jobs import Job, JobKind
from .params import JOB_LOCATION

router = APIRouter(tags=["admin"], responses=problem_responses(400, 401, 422))


@router.post(
    "/admin/reindex",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Re-index every page",
    responses={202: {"headers": JOB_LOCATION}},
)
async def reindex_all(session: Session, request: Request, response: Response) -> Job:
    """Chunks and embeds every ready page again, e.g. after switching the embedding model.

    Pages stay searchable with their old chunks until their new ones are in. Calls made while a
    re-index is still queued share its job.
    """
    job = await jobs.enqueue_once(session, JobKind.REINDEX_ALL)
    await session.commit()
    response.headers["Location"] = request.url_for("get_job", jobId=job.id).path
    return Job.from_db(job)
