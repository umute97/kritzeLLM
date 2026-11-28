"""Cursor pagination: each page picks up right after the last row of the one before."""

import re
from collections.abc import Callable

from sqlalchemy import Select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import InstrumentedAttribute


async def paginate[T](
    session: AsyncSession, query: Select[T], *, limit: int, cursor_of: Callable[[T], str]
) -> tuple[list[T], str | None]:
    """One page of `query`'s rows, plus the cursor for the next page (`None` on the last one).

    `query` comes ordered and already narrowed to the rows after the current cursor.
    """
    rows = list((await session.scalars(query.limit(limit + 1))).all())
    if len(rows) <= limit:
        return rows, None
    return rows[:limit], cursor_of(rows[limit - 1])


def newest_first[T](
    query: Select[T], id_column: InstrumentedAttribute[str], cursor: str | None
) -> Select[T]:
    """`query` ordered by its UUIDv7 IDs, newest first, from right after the ID in `cursor`."""
    if cursor is not None:
        query = query.where(id_column < cursor)
    return query.order_by(id_column.desc())


def join_cursor(key: str, number: int) -> str:
    return f"{key}.{number}"


def split_cursor(cursor: str, pattern: str) -> tuple[str, int]:
    """The key and number in a `key.number` cursor. Raises `ValueError` unless it fits `pattern`."""
    if not re.fullmatch(pattern, cursor):
        raise ValueError(f"Malformed cursor {cursor!r}")
    key, _, number = cursor.partition(".")
    return key, int(number)
