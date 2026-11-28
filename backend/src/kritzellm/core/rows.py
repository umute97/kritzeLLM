"""Plain row access that needs no domain logic: fetching one, adding one, changing one."""

from collections.abc import Mapping
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from .errors import NotFoundError


async def get_existing[T](session: AsyncSession, model: type[T], ident: str, **options: Any) -> T:
    """The `model` row with primary key `ident`. Raises `NotFoundError` if there's none."""
    row = await session.get(model, ident, **options)
    if row is None:
        raise NotFoundError(model.__name__)
    return row


async def add_new[T](session: AsyncSession, row: T) -> T:
    """Inserts `row` and loads what the database filled in. The caller commits."""
    session.add(row)
    await session.flush()
    await session.refresh(row)
    return row


async def update_existing[T](
    session: AsyncSession, model: type[T], ident: str, changes: Mapping[str, Any]
) -> T:
    """Applies `changes` to the `model` row with primary key `ident`. The caller commits.

    Raises `NotFoundError` if there's no such row.
    """
    row = await get_existing(session, model, ident)
    for field, value in changes.items():
        setattr(row, field, value)
    await session.flush()
    await session.refresh(row)
    return row
