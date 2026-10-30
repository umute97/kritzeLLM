import asyncio
from collections.abc import Sequence
from typing import Any

import pytest
from pydantic_ai.embeddings import EmbeddingResult, EmbeddingSettings, TestEmbeddingModel
from pydantic_ai.embeddings.openai import OpenAIEmbeddingModel

from kritzellm.config import Settings
from kritzellm.core import embeddings
from kritzellm.core.embeddings import EMBED_DIMENSIONS, embed


class RecordingModel(TestEmbeddingModel):
    """The fake model, keeping each request's texts and settings."""

    def __init__(self) -> None:
        super().__init__()
        self.calls: list[tuple[list[str], EmbeddingSettings | None]] = []

    async def embed(
        self, inputs: str | Sequence[str], *, input_type: Any, settings: Any = None
    ) -> EmbeddingResult:
        self.calls.append(([inputs] if isinstance(inputs, str) else list(inputs), settings))
        return await super().embed(inputs, input_type=input_type, settings=settings)


def _settings(**overrides: Any) -> Settings:
    return Settings(
        **{"embed_model": "text-embedding-3-small", "openai_api_key": "sk-test", **overrides}
    )


def test_the_test_model_needs_no_key() -> None:
    vectors = asyncio.run(
        embed(["eins", "zwei"], _settings(embed_model="test", openai_api_key=None))
    )

    assert [len(vector) for vector in vectors] == [EMBED_DIMENSIONS, EMBED_DIMENSIONS]


def test_openai_is_asked_for_full_size_vectors_in_batches(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(embeddings, "BATCH_SIZE", 2)
    embedder = embeddings._embedder("text-embedding-3-small", "sk-test")
    assert isinstance(embedder.model, OpenAIEmbeddingModel)
    assert embedder.model.model_name == "text-embedding-3-small"
    fake = RecordingModel()

    with embedder.override(model=fake):
        vectors = asyncio.run(embed(["a", "b", "c", "d", "e"], _settings()))

    assert len(vectors) == 5
    assert [texts for texts, _ in fake.calls] == [["a", "b"], ["c", "d"], ["e"]]
    assert [settings and settings.get("dimensions") for _, settings in fake.calls] == [
        EMBED_DIMENSIONS
    ] * 3


def test_nothing_to_embed_makes_no_request() -> None:
    fake = RecordingModel()
    embedder = embeddings._embedder("text-embedding-3-small", "sk-test")

    with embedder.override(model=fake):
        assert asyncio.run(embed([], _settings())) == []

    assert fake.calls == []
