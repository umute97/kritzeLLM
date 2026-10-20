"""The `/api/v1` application and the OpenAPI document it generates."""

import json
from typing import Any

from fastapi import Depends, FastAPI
from fastapi.openapi.utils import get_openapi
from fastapi.routing import APIRoute
from pydantic.alias_generators import to_camel

from kritzellm import __version__
from kritzellm.config import Settings
from kritzellm.db import create_engine, create_sessionmaker

from . import API_PREFIX
from .auth import require_token
from .deps import check_query_params
from .errors import PROBLEM_JSON, install_problem_handlers
from .routes import blocks, docs, health, jobs, journals, pages

DESCRIPTION = """\
Upload photos of handwritten journal pages and review their transcriptions. Search and a chat agent
that cites the exact page are coming. 🖍️

## Conventions

- **Base path** `/api/v1`. JSON bodies use `camelCase`.
- **Timestamps** are RFC 3339 (`2026-10-10T09:30:00Z`); journal dates are `YYYY-MM-DD`.
- **IDs** are [TypeIDs](https://github.com/jetify-com/typeid): a type prefix plus a base32-encoded
  UUIDv7, e.g. `pg_01k7c9a3b5d7e9f1g3h5j7k9m1`. Prefixes: `jrn` journal, `pg` page, `blk` block,
  `job` job.
- **Errors** are [RFC 9457](https://www.rfc-editor.org/rfc/rfc9457) `application/problem+json`.
  `400` means the request couldn't be parsed; `422` means a value is invalid (including malformed
  IDs) and lists each problem in `errors`. A well-formed ID that doesn't exist is a `404`.
- **Lists** use cursor pagination: pass `limit` and the previous response's `nextCursor` as
  `cursor`. `nextCursor` is `null` on the last page. Treat cursors as opaque strings; they stay
  valid even if the last item you got is deleted meanwhile.
- **Long-running work** (transcribing, re-indexing) answers `202 Accepted` with a `Job`
  and a `Location` header. Poll the job until it finishes.
- **Auth**: when the server has an `API_TOKEN` configured, every request except `GET /health`
  needs `Authorization: Bearer <token>`.
"""

TAGS = [
    {"name": "health", "description": "Service status."},
    {"name": "journals", "description": "Notebooks (or volumes) that pages belong to."},
    {"name": "pages", "description": "Uploaded page images and their transcriptions."},
    {"name": "blocks", "description": "Text on a page (paragraphs, lists, margin notes)."},
    {"name": "jobs", "description": "Background work and its progress."},
]


def _operation_id(route: APIRoute) -> str:
    return to_camel(route.name)


def create_api(settings: Settings | None = None) -> FastAPI:
    """The API app. The docs are at `/docs` and the generated spec at `/openapi.json`."""
    api = FastAPI(
        title="kritzeLLM API",
        version=__version__,
        summary="Search and chat with a handwritten journal.",
        description=DESCRIPTION,
        openapi_tags=TAGS,
        servers=[{"url": API_PREFIX, "description": "Relative to wherever the app runs."}],
        root_path_in_servers=False,
        generate_unique_id_function=_operation_id,
        separate_input_output_schemas=False,
        docs_url=None,
        redoc_url=None,
        dependencies=[Depends(check_query_params)],
    )
    api.state.settings = settings = settings or Settings()
    api.state.db_engine = create_engine(settings)
    api.state.sessionmaker = create_sessionmaker(api.state.db_engine)
    install_problem_handlers(api)

    api.include_router(docs.router)
    api.include_router(health.router)
    authed = [Depends(require_token)]
    for module in (journals, pages, blocks, jobs):
        api.include_router(module.router, dependencies=authed)

    def openapi() -> dict[str, Any]:
        if api.openapi_schema is None:
            api.openapi_schema = build_openapi(api)
        return api.openapi_schema

    api.openapi = openapi  # type: ignore[method-assign]
    return api


def render_openapi() -> str:
    """The OpenAPI document exactly as committed to `api/openapi.json`."""
    spec = _whole_numbers_as_ints(create_api().openapi())
    return json.dumps(spec, indent=2, ensure_ascii=False) + "\n"


def _whole_numbers_as_ints(value: Any) -> Any:
    if isinstance(value, float) and value.is_integer():
        return int(value)
    if isinstance(value, dict):
        return {key: _whole_numbers_as_ints(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_whole_numbers_as_ints(item) for item in value]
    return value


def build_openapi(api: FastAPI) -> dict[str, Any]:
    """FastAPI's OpenAPI document, tidied up for clients."""
    spec = get_openapi(
        title=api.title,
        version=api.version,
        summary=api.summary,
        description=api.description,
        routes=api.routes,
        tags=api.openapi_tags,
        servers=api.servers,
        separate_input_output_schemas=False,
    )
    schemas: dict[str, Any] = spec["components"]["schemas"]

    # Errors are problem+json
    for operations in spec["paths"].values():
        for operation in operations.values():
            for code, response in operation.get("responses", {}).items():
                content = response.get("content", {})
                if code.startswith(("4", "5")) and "application/json" in content:
                    content[PROBLEM_JSON] = content.pop("application/json")

    # FastAPI's generated validation-error schemas are replaced by Problem
    for name in ("HTTPValidationError", "ValidationError"):
        schemas.pop(name, None)

    # The multipart upload body gets a proper name.
    renames = {name: "PageUpload" for name in schemas if name.startswith("Body_uploadPages")}

    text = json.dumps(spec)
    for old, new in renames.items():
        text = text.replace(f"#/components/schemas/{old}", f"#/components/schemas/{new}")
        text = text.replace(f'"{old}":', f'"{new}":')
    spec = json.loads(text)
    spec["components"]["schemas"] = dict(sorted(spec["components"]["schemas"].items()))
    return spec
