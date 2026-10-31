"""Schemathesis fuzzes every endpoint from api/openapi.json and checks every answer against it."""

from pathlib import Path

import pytest
import schemathesis
from hypothesis import settings
from pydantic import PostgresDsn, SecretStr

from kritzellm.config import Settings
from kritzellm.main import create_app

pytestmark = pytest.mark.db

TOKEN = "fuzz-token"


@pytest.fixture
def api_schema(database_url: str, data_dir: Path) -> schemathesis.BaseSchema:
    settings = Settings(
        api_token=SecretStr(TOKEN),
        database_url=PostgresDsn(database_url),
        data_dir=data_dir,
        embed_model="test",
    )
    app = create_app(settings)
    api_schema = schemathesis.openapi.from_asgi("/api/v1/openapi.json", app)
    # Through the config, so the fuzzer knows requests carry the token and can still leave it out.
    api_schema.config.update(headers={"Authorization": f"Bearer {TOKEN}"})
    return api_schema


schema = schemathesis.pytest.from_fixture("api_schema")


@schema.parametrize()
@settings(max_examples=50, deadline=None)
def test_api_matches_its_spec(case: schemathesis.Case) -> None:
    case.call_and_validate()
