import asyncio
import contextlib
import io
import os
from collections.abc import AsyncIterator, Callable, Iterator
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient
from PIL import ExifTags, Image
from pydantic import PostgresDsn
from pydantic_ai.messages import ModelMessage, ModelResponse, ToolCallPart
from pydantic_ai.models.function import AgentInfo, FunctionModel
from sqlalchemy import make_url, text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from kritzellm.config import Settings
from kritzellm.core import transcribe
from kritzellm.db.migrate import upgrade
from kritzellm.main import create_app
from kritzellm.worker import Worker

# Nothing listens on port 1, so connecting fails right away.
UNREACHABLE_DATABASE_URL = "postgresql+asyncpg://kritzellm:kritzellm@127.0.0.1:1/kritzellm"


@pytest.fixture
def make_client() -> Callable[..., TestClient]:
    """Builds an API client whose settings don't depend on the environment (or a local `.env`)."""

    def make(**settings: Any) -> TestClient:
        settings = {"api_token": None, "database_url": UNREACHABLE_DATABASE_URL, **settings}
        return TestClient(create_app(Settings(**settings)), base_url="http://test/api/v1")

    return make


@pytest.fixture
def make_image() -> Callable[..., bytes]:
    """Encodes a plain test picture, e.g. `make_image("PNG", size=(40, 30), color="blue")`."""

    def make(
        format: str = "JPEG",
        *,
        size: tuple[int, int] = (300, 200),
        color: str | tuple[int, ...] = "red",
        mode: str = "RGB",
        orientation: int | None = None,
    ) -> bytes:
        image = Image.new(mode, size, color)
        exif = Image.Exif()
        if orientation is not None:
            exif[ExifTags.Base.Orientation] = orientation
            exif[ExifTags.Base.Make] = "Test camera"
        buffer = io.BytesIO()
        image.save(buffer, format, exif=exif)
        return buffer.getvalue()

    return make


class FakeVisionModel:
    """Stands in for the transcription model, answering with queued outputs.

    Each call takes the next of `outputs` (the last one repeats). An output is what the model
    returns as the transcription, or an exception to raise instead.
    """

    def __init__(self) -> None:
        self.outputs: list[dict[str, Any] | Exception] = [
            {"page_label": None, "entry_dates": [], "blocks": []}
        ]
        self.calls: list[tuple[list[ModelMessage], AgentInfo]] = []

    def respond(self, messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        self.calls.append((messages, info))
        output = self.outputs.pop(0) if len(self.outputs) > 1 else self.outputs[0]
        if isinstance(output, Exception):
            raise output
        return ModelResponse(parts=[ToolCallPart(info.output_tools[0].name, output)])


@pytest.fixture
def vision_model() -> Iterator[FakeVisionModel]:
    """Replaces whatever model is configured for transcription."""
    fake = FakeVisionModel()
    with transcribe.agent.override(model=FunctionModel(fake.respond)):
        yield fake


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


async def _recreate_database(url: str, *, create: bool = True) -> None:
    target = make_url(url)
    admin = create_async_engine(target.set(database="postgres"), isolation_level="AUTOCOMMIT")
    try:
        async with admin.connect() as connection:
            await connection.execute(
                text(f'DROP DATABASE IF EXISTS "{target.database}" WITH (FORCE)')
            )
            if create:
                await connection.execute(text(f'CREATE DATABASE "{target.database}"'))
    finally:
        await admin.dispose()


@pytest.fixture(scope="session")
def database_url() -> Iterator[str]:
    """A fresh, migrated database from `TEST_DATABASE_URL` (it's dropped and recreated).

    Without one the DB tests are skipped, unless `KRITZELLM_REQUIRE_DB=1` (as in CI).
    """
    url = os.environ.get("TEST_DATABASE_URL")
    required = os.environ.get("KRITZELLM_REQUIRE_DB") == "1"
    try:
        if not url:
            raise LookupError("TEST_DATABASE_URL isn't set")
        asyncio.run(_recreate_database(url))
    except Exception as exc:
        if required:
            raise
        pytest.skip(f"No test database: {exc}")
    upgrade(url)
    yield url
    asyncio.run(_recreate_database(url, create=False))


@pytest.fixture
def data_dir(tmp_path: Path) -> Path:
    return tmp_path / "data"


@pytest.fixture
def db_client(database_url: str, data_dir: Path) -> Iterator[TestClient]:
    """An API client backed by the test database. One event loop serves the whole test."""
    settings = Settings(api_token=None, database_url=PostgresDsn(database_url), data_dir=data_dir)
    app = create_app(settings)
    with TestClient(app, base_url="http://test/api/v1") as client:
        yield client


@pytest.fixture
def settings(database_url: str, data_dir: Path) -> Settings:
    """The worker's settings: the fake `test` model, unless a test swaps in `vision_model`."""
    return Settings(
        api_token=None,
        database_url=PostgresDsn(database_url),
        data_dir=data_dir,
        transcribe_model="test",
    )


@pytest.fixture
def work(settings: Settings) -> Callable[[], None]:
    """Runs the worker until no jobs are queued."""

    async def run() -> None:
        async with contextlib.aclosing(Worker(settings)) as worker:
            await worker.run_until_idle()

    return lambda: asyncio.run(run())


@pytest.fixture
async def session(database_url: str) -> AsyncIterator[AsyncSession]:
    engine = create_async_engine(database_url)
    async with AsyncSession(engine, expire_on_commit=False) as session:
        yield session
    await engine.dispose()
