from fastapi import APIRouter

from kritzellm.core import blocks as core
from kritzellm.core.errors import get_existing
from kritzellm.db import models as db

from ..deps import Session
from ..errors import problem_responses
from ..schemas.blocks import Block, BlockUpdate, BlockUpdateResult
from ..schemas.jobs import Job
from .params import BlockIdPath

router = APIRouter(tags=["blocks"], responses=problem_responses(400, 401, 422))


@router.get(
    "/blocks/{blockId}",
    summary="Get a block",
    responses=problem_responses(404),
)
async def get_block(block_id: BlockIdPath, session: Session) -> Block:
    """Returns a single block. Handy for resolving a chat source."""
    return Block.model_validate(await get_existing(session, db.Block, block_id))


@router.patch(
    "/blocks/{blockId}",
    summary="Fix a block",
    responses=problem_responses(404, 409),
)
async def update_block(
    block_id: BlockIdPath, body: BlockUpdate, session: Session
) -> BlockUpdateResult:
    """Corrects a block's text, kind or `uncertain` flag. Its page is re-indexed in the background.

    Edits made in a row share one re-index job while it's still queued. Returns `409` while the page
    is waiting to be read or being read.
    """
    changes = body.model_dump(exclude_unset=True, by_alias=False)
    block, job = await core.update_block(session, block_id, changes)
    await session.commit()
    return BlockUpdateResult(block=Block.model_validate(block), job=Job.from_db(job))
