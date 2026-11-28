"""Turning text into vectors for search.

With the `test` model, every vector is the same, so they're no use for actually finding anything.
"""

import logging
from collections.abc import Sequence

from pydantic_ai.exceptions import ModelAPIError, UserError

from kritzellm.config import Settings

from . import llm
from .errors import UpstreamError

logger = logging.getLogger(__name__)

BATCH_SIZE = 256
"""Most texts sent in one request (OpenAI takes up to 2048)."""


async def embed(texts: Sequence[str], settings: Settings) -> list[list[float]]:
    """Embeds texts for storing, in order, with the configured model."""
    name = settings.embed_model
    embedder = llm.embedder(settings)
    vectors: list[list[float]] = []
    tokens = 0
    for start in range(0, len(texts), BATCH_SIZE):
        result = await embedder.embed_documents(texts[start : start + BATCH_SIZE])
        vectors.extend(list(vector) for vector in result.embeddings)
        tokens += result.usage.input_tokens
    if texts:
        logger.info("Embedded %d text(s) with %s: %d tokens", len(texts), name, tokens)
    return vectors


async def embed_query(text: str, settings: Settings) -> list[float]:
    """Embeds a search query with the configured model.

    Raises `UpstreamError` if the model isn't set up (no API key) or the API fails.
    """
    try:
        result = await llm.embedder(settings).embed_query(text)
    except UserError as exc:
        logger.error("The embedding model isn't set up: %s", exc)
        raise UpstreamError("The embedding model isn't set up on the server.") from exc
    except ModelAPIError as exc:
        logger.warning("Embedding a search query failed: %s", exc)
        raise UpstreamError("The embedding model couldn't be reached. Try again later.") from exc
    return list(result.embeddings[0])
