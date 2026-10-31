"""What can go wrong in the domain. Messages are written for the client; the API picks the status."""

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession


class NotFoundError(Exception):
    """Something doesn't exist (any more)."""

    def __init__(self, what: str) -> None:
        super().__init__(f"{what} not found.")


class ConflictError(Exception):
    """The request clashes with the current state, e.g. a job is still running."""


class PageBusyError(ConflictError):
    """The page is waiting to be read or being read, which would undo any change."""

    def __init__(self) -> None:
        super().__init__("This page is still being read. Try again once its job is done.")


class PageNumberTakenError(ConflictError):
    """Another page of the journal already has the page number."""


class UpstreamError(Exception):
    """A service the request relies on (e.g. OpenAI) failed or couldn't be reached."""


async def get_existing[T](session: AsyncSession, model: type[T], ident: str, **options: Any) -> T:
    """The `model` row with primary key `ident`. Raises `NotFoundError` if there's none."""
    row = await session.get(model, ident, **options)
    if row is None:
        raise NotFoundError(model.__name__)
    return row
