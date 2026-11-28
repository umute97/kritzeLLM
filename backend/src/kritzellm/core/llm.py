"""The OpenAI models, built once and shared by every call.

A model named `test` is PydanticAI's fake instead: made-up output, no API calls, no key needed.
Building a real one without a key raises PydanticAI's `UserError`.
"""

from functools import cache

from openai.types.shared import ReasoningEffort
from pydantic_ai.embeddings import Embedder, EmbeddingModel, TestEmbeddingModel
from pydantic_ai.embeddings.openai import OpenAIEmbeddingModel
from pydantic_ai.models import Model
from pydantic_ai.models.openai import OpenAIResponsesModel, OpenAIResponsesModelSettings
from pydantic_ai.providers.openai import OpenAIProvider

from kritzellm.config import Settings
from kritzellm.domain import EMBED_DIMENSIONS

TEST_MODEL = "test"


def model(name: str, settings: Settings, *, reasoning_effort: ReasoningEffort) -> Model | str:
    """The model an agent runs with."""
    if name == TEST_MODEL:
        return TEST_MODEL
    return _responses_model(name, _api_key(settings), reasoning_effort)


def embedder(settings: Settings) -> Embedder:
    """The embedder for the configured `EMBED_MODEL`."""
    return _embedder(settings.embed_model, _api_key(settings))


def _api_key(settings: Settings) -> str | None:
    key = settings.openai_api_key
    return key.get_secret_value() if key else None


@cache
def _responses_model(name: str, api_key: str | None, reasoning_effort: ReasoningEffort) -> Model:
    return OpenAIResponsesModel(
        name,
        provider=OpenAIProvider(api_key=api_key),
        settings=OpenAIResponsesModelSettings(openai_reasoning_effort=reasoning_effort),
    )


@cache
def _embedder(name: str, api_key: str | None) -> Embedder:
    model: EmbeddingModel
    if name == TEST_MODEL:
        model = TestEmbeddingModel(dimensions=EMBED_DIMENSIONS)
    else:
        model = OpenAIEmbeddingModel(name, provider=OpenAIProvider(api_key=api_key))
    return Embedder(model, settings={"dimensions": EMBED_DIMENSIONS})
