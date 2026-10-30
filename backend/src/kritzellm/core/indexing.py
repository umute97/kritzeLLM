"""Indexing pages for search: their blocks, chunked and embedded.

Indexing takes no lock on the page. A block edited meanwhile queues another re-index, which the
worker only runs after this one, so the last word is always the page's latest text.
"""

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from kritzellm.api.schemas.pages import PageStatus
from kritzellm.config import Settings
from kritzellm.db import models as db

from .chunking import chunk_blocks
from .embeddings import embed


async def index_page(session: AsyncSession, page_id: str, settings: Settings) -> bool:
    """Replaces the page's chunks with fresh ones from its blocks. `False` if the page is gone.

    The caller commits.
    """
    if await session.scalar(select(db.Page.id).where(db.Page.id == page_id)) is None:
        return False
    blocks = await session.execute(
        select(db.Block.id, db.Block.text).where(db.Block.page_id == page_id).order_by(db.Block.seq)
    )
    chunks = chunk_blocks(blocks.all())
    vectors = await embed([chunk.text for chunk in chunks], settings)
    await session.execute(delete(db.Chunk).where(db.Chunk.page_id == page_id))
    session.add_all(
        db.Chunk(
            page_id=page_id,
            seq=seq,
            block_ids=list(chunk.block_ids),
            text=chunk.text,
            embedding=vector,
            embed_model=settings.embed_model,
        )
        for seq, (chunk, vector) in enumerate(zip(chunks, vectors, strict=True))
    )
    await session.flush()
    return True


async def ready_page_ids(session: AsyncSession) -> list[str]:
    """The pages that are fully processed, oldest first."""
    query = select(db.Page.id).where(db.Page.status == PageStatus.READY).order_by(db.Page.id)
    return list((await session.scalars(query)).all())
