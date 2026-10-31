"""Search: finding pages by meaning, by words, or both."""

from enum import StrEnum

from pydantic import Field

from .blocks import Block
from .common import ApiModel
from .pages import Page


class SearchMode(StrEnum):
    """How to search.

    `hybrid` merges `vector` and `keyword` results with reciprocal rank fusion. `vector` finds text
    by meaning, `keyword` by its words (`"quoted phrases"`, `or` and `-word` work). `exact` finds
    blocks containing the query as written, ignoring case.
    """

    HYBRID = "hybrid"
    VECTOR = "vector"
    KEYWORD = "keyword"
    EXACT = "exact"


class SearchHit(ApiModel):
    """A page that matches the search."""

    page: Page
    blocks: list[Block]
    """The blocks that matched, in reading order: the page's best matching chunk, or for `exact` every block containing the query."""
    score: float
    """How well the page matches, higher is better. Only comparable within one search: the fused score for `hybrid`, cosine similarity for `vector`, `ts_rank_cd` for `keyword`, and the number of matching blocks for `exact`."""
    vector_rank: int | None = Field(ge=1)
    """Position of the hit's chunk among the vector matches, from 1; `null` if it isn't among them or vectors weren't searched."""
    keyword_rank: int | None = Field(ge=1)
    """Position of the hit's chunk among the keyword matches, from 1; `null` if it isn't among them or keywords weren't searched."""


class SearchResult(ApiModel):
    """The best matching pages, best first."""

    items: list[SearchHit]
