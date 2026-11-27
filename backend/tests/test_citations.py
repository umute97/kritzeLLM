from datetime import date

from kritzellm.api.schemas.blocks import BlockKind
from kritzellm.core.agent.citations import Citations, strip_citations
from kritzellm.db import models as db
from kritzellm.ids import Prefix, new_id

PAGE = db.Page(
    id=new_id(Prefix.PAGE),
    journal_id=new_id(Prefix.JOURNAL),
    page_number=12,
    entry_dates=[date(2026, 3, 3)],
)


def block(text: str) -> db.Block:
    return db.Block(
        id=new_id(Prefix.BLOCK), page_id=PAGE.id, seq=0, kind=BlockKind.PARAGRAPH, text=text
    )


def test_a_block_keeps_its_number() -> None:
    citations = Citations()
    peas, rain = block("Sweet peas."), block("Rain.")

    assert [citations.ref(peas, PAGE), citations.ref(rain, PAGE), citations.ref(peas, PAGE)] == [
        1,
        2,
        1,
    ]
    source = citations.get(1)
    assert source is not None
    assert (source.block_id, source.page_number, source.quote) == (peas.id, 12, "Sweet peas.")
    assert citations.get(3) is None


def test_finish_drops_unread_citations_and_lists_sources_in_order() -> None:
    citations = Citations()
    for text in ("One.", "Two.", "Three."):
        citations.ref(block(text), PAGE)

    text, sources = citations.finish(
        "First [3], then [9]. Both [2, 9, 3, 2] and [1][7], but not [8, 9]."
    )

    assert text == "First [3], then. Both [2, 3] and [1], but not."
    assert [source.ref for source in sources] == [3, 2, 1]


def test_finish_leaves_other_brackets_alone() -> None:
    text, sources = Citations().finish("A [link](https://example.com) and [?] and [a1].")

    assert text == "A [link](https://example.com) and [?] and [a1]."
    assert sources == []


def test_strip_citations() -> None:
    assert strip_citations("By the fence [3][5], in March [1, 2].") == "By the fence, in March."
