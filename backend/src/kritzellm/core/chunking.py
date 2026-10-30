"""Cutting a page's blocks into chunks of about 120 to 350 words, the pieces that get embedded.

Consecutive blocks are merged greedily, so a chunk never spans two pages. A block too long for one
chunk is split into even runs of words.
"""

import math
from collections.abc import Sequence
from dataclasses import dataclass

MIN_WORDS = 120
"""A last chunk shorter than this takes blocks over from the one before it, where it can."""
MAX_WORDS = 350


@dataclass(frozen=True, slots=True)
class Chunk:
    block_ids: tuple[str, ...]
    """The blocks the text comes from, in order."""
    text: str


@dataclass(frozen=True, slots=True)
class _Piece:
    block_id: str
    text: str
    words: int


def _pieces(block_id: str, text: str) -> list[_Piece]:
    """The block whole, or split into even runs of at most `MAX_WORDS` words."""
    words = text.split()
    if len(words) <= MAX_WORDS:
        return [_Piece(block_id, text.strip(), len(words))]
    size = math.ceil(len(words) / math.ceil(len(words) / MAX_WORDS))
    runs = [words[start : start + size] for start in range(0, len(words), size)]
    return [_Piece(block_id, " ".join(run), len(run)) for run in runs]


def _chunk(pieces: Sequence[_Piece]) -> Chunk:
    block_ids = tuple(dict.fromkeys(piece.block_id for piece in pieces))
    return Chunk(block_ids, "\n\n".join(piece.text for piece in pieces))


def chunk_blocks(blocks: Sequence[tuple[str, str]]) -> list[Chunk]:
    """Chunks one page's blocks, given as `(id, text)` in reading order.

    Blocks without words are left out.
    """
    groups: list[list[_Piece]] = []
    words = 0
    for block_id, text in blocks:
        for piece in _pieces(block_id, text):
            if not piece.words:
                continue
            if groups and words + piece.words <= MAX_WORDS:
                groups[-1].append(piece)
                words += piece.words
            else:
                groups.append([piece])
                words = piece.words
    if len(groups) > 1 and words < MIN_WORDS:
        groups[-2:] = _rebalance(groups[-2] + groups[-1])
    return [_chunk(group) for group in groups]


def _rebalance(pieces: list[_Piece]) -> list[list[_Piece]]:
    """Splits the pieces in two where the longer side is shortest, so a short tail grows."""
    total = sum(piece.words for piece in pieces)
    best, best_longer, left = 1, total, 0
    for split in range(1, len(pieces)):
        left += pieces[split - 1].words
        if (longer := max(left, total - left)) < best_longer:
            best, best_longer = split, longer
    return [pieces[:best], pieces[best:]]
