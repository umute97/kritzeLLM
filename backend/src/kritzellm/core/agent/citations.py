"""Numbering the blocks the helper reads during one answer, so the answer can cite them as `[n]`."""

import re

from kritzellm.api.schemas.conversations import Source
from kritzellm.db import models as db

_CITATION = re.compile(r"(\s?)\[(\d+(?:\s*,\s*\d+)*)\]")
"""`[3]` or `[3, 5]`, with the space before it."""


class Citations:
    """The blocks the helper has seen while answering, each with its number."""

    def __init__(self) -> None:
        self._by_ref: dict[int, Source] = {}
        self._refs: dict[str, int] = {}

    def ref(self, block: db.Block, page: db.Page) -> int:
        """The block's number, the same every time it comes up."""
        if (known := self._refs.get(block.id)) is not None:
            return known
        ref = len(self._refs) + 1
        self._refs[block.id] = ref
        self._by_ref[ref] = Source(
            ref=ref,
            block_id=block.id,
            page_id=page.id,
            journal_id=page.journal_id,
            page_number=page.page_number,
            entry_dates=page.entry_dates,
            quote=block.text,
        )
        return ref

    def get(self, ref: int) -> Source | None:
        return self._by_ref.get(ref)

    def finish(self, answer: str) -> tuple[str, list[Source]]:
        """The answer without citations of blocks the helper never saw, and the sources it does
        cite, in the order it first cites them."""
        cited: dict[int, Source] = {}

        def keep_known(match: re.Match[str]) -> str:
            refs = dict.fromkeys(int(ref) for ref in re.split(r"\s*,\s*", match[2]))
            known = [ref for ref in refs if ref in self._by_ref]
            for ref in known:
                cited.setdefault(ref, self._by_ref[ref])
            return f"{match[1]}[{', '.join(map(str, known))}]" if known else ""

        return _CITATION.sub(keep_known, answer), list(cited.values())


def strip_citations(text: str) -> str:
    """Text without its `[n]` citations, whose numbers only meant something in their own answer."""
    return _CITATION.sub("", text)
