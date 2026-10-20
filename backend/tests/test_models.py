import hashlib

import pytest
from sqlalchemy import delete, func, select, text
from sqlalchemy.exc import IntegrityError, StatementError
from sqlalchemy.ext.asyncio import AsyncSession

from kritzellm.api.schemas.blocks import BlockKind
from kritzellm.api.schemas.pages import PageStatus
from kritzellm.db.models import Block, Journal, Page
from kritzellm.ids import Prefix, decode, new_id

pytestmark = [pytest.mark.db, pytest.mark.anyio]


def _page(journal: Journal, number: int, content: bytes | None = None) -> Page:
    return Page(
        journal=journal,
        page_number=number,
        original_filename=f"page-{number}.jpg",
        original_media_type="image/jpeg",
        sha256=hashlib.sha256(content or f"page {number}".encode()).digest(),
        width=1536,
        height=2048,
    )


def _block(page: Page, seq: int, text: str) -> Block:
    return Block(page=page, seq=seq, kind=BlockKind.PARAGRAPH, text=text)


async def _journal_with_a_page(session: AsyncSession) -> tuple[Journal, Page]:
    journal = Journal(name="Summer 2026")
    page = _page(journal, 1)
    session.add_all([journal, page, _block(page, 0, "Flew to Lisbon today.")])
    await session.commit()
    return journal, page


async def test_rows_round_trip_with_typeids(session: AsyncSession) -> None:
    journal, page = await _journal_with_a_page(session)
    session.expunge_all()

    stored = await session.scalar(select(Page).where(Page.id == page.id))
    assert stored is not None
    assert stored.id.startswith("pg_")
    assert decode(Prefix.PAGE, stored.id).version == 7
    assert stored.journal_id == journal.id
    assert stored.status is PageStatus.UPLOADED
    assert stored.entry_dates == []
    assert stored.created_at.tzinfo is not None

    block = await session.scalar(select(Block).where(Block.page_id == page.id))
    assert block is not None
    assert block.id.startswith("blk_")


async def test_same_file_twice_in_a_journal_is_rejected(session: AsyncSession) -> None:
    journal = Journal(name="Dupes")
    session.add_all([_page(journal, 1, b"same photo"), _page(journal, 2, b"same photo")])
    with pytest.raises(IntegrityError, match="uq_pages_journal_id_sha256"):
        await session.commit()


async def test_pages_can_swap_numbers_in_one_transaction(session: AsyncSession) -> None:
    journal = Journal(name="Swaps")
    first, second = _page(journal, 1), _page(journal, 2)
    session.add_all([journal, first, second])
    await session.commit()

    first.page_number, second.page_number = 2, 1
    await session.commit()

    numbers = await session.execute(
        select(Page.id, Page.page_number).where(Page.journal_id == journal.id)
    )
    assert {page_id: number for page_id, number in numbers} == {first.id: 2, second.id: 1}


async def test_page_numbers_stay_unique(session: AsyncSession) -> None:
    journal = Journal(name="Clash")
    session.add_all([_page(journal, 1, b"a"), _page(journal, 1, b"b")])
    with pytest.raises(IntegrityError, match="uq_pages_journal_id_page_number"):
        await session.commit()


async def test_enum_columns_only_take_api_values(session: AsyncSession) -> None:
    _, page = await _journal_with_a_page(session)
    with pytest.raises(IntegrityError, match="ck_pages_status_valid"):
        await session.execute(
            text("UPDATE pages SET status = 'done' WHERE id = :id"),
            {"id": decode(Prefix.PAGE, page.id)},
        )


async def test_ids_with_the_wrong_prefix_are_rejected(session: AsyncSession) -> None:
    with pytest.raises(StatementError, match="Expected a 'pg' TypeID"):
        await session.get(Page, new_id(Prefix.JOURNAL))


async def test_deleting_a_journal_deletes_its_pages_and_blocks(session: AsyncSession) -> None:
    journal, page = await _journal_with_a_page(session)
    await session.execute(delete(Journal).where(Journal.id == journal.id))
    await session.commit()

    for page_column in (Page.id, Block.page_id):
        assert await session.scalar(select(func.count()).where(page_column == page.id)) == 0
