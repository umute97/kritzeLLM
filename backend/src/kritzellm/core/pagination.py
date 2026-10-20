"""Cursor pagination"""

from sqlalchemy import Row, Select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import InstrumentedAttribute


async def paginate[*Ts](
    session: AsyncSession,
    query: Select[*Ts],
    *,
    id_column: InstrumentedAttribute[str],
    limit: int,
    cursor: str | None,
) -> tuple[list[Row[*Ts]], str | None]:
    """One page of `query`'s rows, plus the cursor for the next page (`None` on the last one).

    `id_column` must be a `TypeId` column of the rows' first entity.
    """
    if cursor is not None:
        query = query.where(id_column < cursor)
    rows = (await session.execute(query.order_by(id_column.desc()).limit(limit + 1))).all()
    page = list(rows[:limit])
    if len(rows) <= limit:
        return page, None
    return page, getattr(page[-1][0], id_column.key)
