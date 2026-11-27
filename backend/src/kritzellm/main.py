"""The ASGI app: the API lives under `/api/v1` (the web app will be served next to it)."""

import logging
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


def _show_app_logs() -> None:
    """Uvicorn only sets up its own loggers, so the app's (e.g. token use) get a handler too."""
    logger = logging.getLogger("kritzellm")
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter("%(levelname)s [%(name)s] %(message)s"))
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)


_show_app_logs()
app = create_app()
