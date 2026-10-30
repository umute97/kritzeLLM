"""Turning text into vectors for search.

The model name `test` swaps in PydanticAI's fake embedding model, so the stack runs without an
OpenAI key. Its vectors are all the same, so they're no use for actually finding anything.
"""

import logging
from collections.abc import Sequence
from functools import cache

from pydantic_ai.embeddings import Embedder, EmbeddingModel, TestEmbeddingModel
from pydantic_ai.embeddings.openai import OpenAIEmbeddingModel
from pydantic_ai.providers.openai import OpenAIProvider

from kritzellm.config import Settings

logger = logging.getLogger(__name__)

TEST_MODEL = "test"
"""Model name for PydanticAI's fake embedding model: dummy vectors, no API calls."""

EMBED_DIMENSIONS = 1536
"""Length of every stored vector: `text-embedding-3-small`'s own, and asked of other models too."""

BATCH_SIZE = 256
"""Most texts sent in one request (OpenAI takes up to 2048)."""


@cache
def _embedder(name: str, api_key: str | None) -> Embedder:
    """One embedder (and HTTP client) per model name and key."""
    model: EmbeddingModel
    if name == TEST_MODEL:
        model = TestEmbeddingModel(dimensions=EMBED_DIMENSIONS)
    else:
        model = OpenAIEmbeddingModel(name, provider=OpenAIProvider(api_key=api_key))
    return Embedder(model, settings={"dimensions": EMBED_DIMENSIONS})


async def embed(texts: Sequence[str], settings: Settings) -> list[list[float]]:
    """Embeds texts for storing, in order, with the configured model."""
    name = settings.embed_model
    api_key = settings.openai_api_key
    embedder = _embedder(name, api_key.get_secret_value() if api_key else None)
    vectors: list[list[float]] = []
    tokens = 0
    for start in range(0, len(texts), BATCH_SIZE):
        result = await embedder.embed_documents(texts[start : start + BATCH_SIZE])
        vectors.extend(list(vector) for vector in result.embeddings)
        tokens += result.usage.input_tokens
    if texts:
        logger.info("Embedded %d text(s) with %s: %d tokens", len(texts), name, tokens)
    return vectors
