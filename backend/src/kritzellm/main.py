"""The ASGI app: the API lives under `/api/v1` (the web app will be served next to it)."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from .api import API_PREFIX
from .api.app import create_api
from .api.errors import install_problem_handlers
from .config import Settings, get_settings


def create_app(settings: Settings | None = None) -> FastAPI:
    api = create_api(settings or get_settings())

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncGenerator[None]:
        yield
        await api.state.db_engine.dispose()

    app = FastAPI(openapi_url=None, docs_url=None, redoc_url=None, lifespan=lifespan)
    install_problem_handlers(app)
    app.mount(API_PREFIX, api)
    return app


app = create_app()
