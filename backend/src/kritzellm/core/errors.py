"""What can go wrong in the domain. Messages are written for the client; the API picks the status."""


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
