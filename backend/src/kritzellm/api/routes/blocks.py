from fastapi import APIRouter

from kritzellm.db import models as db

from ..errors import not_implemented, problem_responses
from ..schemas.blocks import Block, BlockUpdate, BlockUpdateResult
from .params import BlockIdPath

router = APIRouter(tags=["blocks"])


def block_out(block: db.Block) -> Block:
    return Block(
        id=block.id,
        page_id=block.page_id,
        seq=block.seq,
        kind=block.kind,
        text=block.text,
        uncertain=block.uncertain,
    )


@router.get(
    "/blocks/{blockId}",
    summary="Get a block",
    responses=problem_responses(400, 401, 404, 422),
)
async def get_block(block_id: BlockIdPath) -> Block:
    """Returns a single block. Handy for resolving a chat source."""
    not_implemented()


@router.patch(
    "/blocks/{blockId}",
    summary="Fix a block",
    responses=problem_responses(400, 401, 404, 422),
)
async def update_block(block_id: BlockIdPath, body: BlockUpdate) -> BlockUpdateResult:
    """Corrects a block's text, kind or `uncertain` flag. Its page is re-indexed in the background."""
    not_implemented()
