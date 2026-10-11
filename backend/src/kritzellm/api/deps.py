"""Dependencies shared by the routes."""

from collections.abc import AsyncGenerator
from typing import Any, get_args, get_origin

from fastapi import Request
from fastapi.dependencies.models import Dependant
from fastapi.exceptions import RequestValidationError
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

from kritzellm.config import Settings


def get_settings(request: Request) -> Settings:
    """The settings the running API was created with."""
    return request.app.state.settings


def get_db_engine(request: Request) -> AsyncEngine:
    return request.app.state.db_engine


async def get_session(request: Request) -> AsyncGenerator[AsyncSession]:
    """A database session for one request. Routes commit their own changes."""
    async with request.app.state.sessionmaker() as session:
        yield session


def _is_list(annotation: Any) -> bool:
    """`list[str]`, `set[int] | None`, …: types a repeated query parameter fills."""
    types = (annotation, *get_args(annotation))
    return any(get_origin(type_) in (list, set, tuple, frozenset) for type_ in types)


def _query_params(dependant: Dependant) -> dict[str, bool]:
    """The query parameters a route declares, each mapped to whether it may repeat (lists)."""
    params = {
        param.alias: _is_list(param.field_info.annotation) for param in dependant.query_params
    }
    for sub in dependant.dependencies:
        params |= _query_params(sub)
    return params


def check_query_params(request: Request) -> None:
    """A `422` for undeclared or repeated query parameters.

    Without it, a typo like `?limt=5` would be ignored and `?limit=5&limit=50` would quietly use 50.
    """
    dependant = getattr(request.scope.get("route"), "dependant", None)
    if dependant is None:
        return
    declared = _query_params(dependant)
    errors = []
    for name in sorted(set(request.query_params)):
        if name not in declared:
            errors.append(
                {
                    "type": "extra_forbidden",
                    "loc": ("query", name),
                    "msg": "Unknown query parameter",
                }
            )
        elif not declared[name] and len(request.query_params.getlist(name)) > 1:
            errors.append(
                {"type": "too_long", "loc": ("query", name), "msg": "Give this parameter only once"}
            )
    if errors:
        raise RequestValidationError(errors)
