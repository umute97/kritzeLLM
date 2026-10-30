"""Server settings, read from environment variables (see `.env.example`)."""

from functools import lru_cache
from pathlib import Path

from pydantic import PostgresDsn, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_ignore_empty=True, extra="ignore")

    database_url: PostgresDsn = PostgresDsn(
        "postgresql+asyncpg://kritzellm:kritzellm@localhost:5432/kritzellm"
    )
    """SQLAlchemy URL of the Postgres database."""
    api_token: SecretStr | None = None
    """When set, every API request (except `/health`) needs `Authorization: Bearer <token>`."""
    data_dir: Path = Path("data")
    """Where page images are stored."""

    openai_api_key: SecretStr | None = None
    """Key for the OpenAI API. Not needed when both models are `test`."""
    transcribe_model: str = "gpt-6-luna"
    """OpenAI model that reads page images. `test` fakes it: made-up text, no API calls."""
    embed_model: str = "text-embedding-3-small"
    """OpenAI model that embeds page text for search. `test` fakes it: dummy vectors, no API calls."""


@lru_cache
def get_settings() -> Settings:
    return Settings()
