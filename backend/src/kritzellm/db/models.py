"""The database tables."""

from datetime import date, datetime
from enum import StrEnum
from typing import Any

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    CheckConstraint,
    Computed,
    Date,
    DateTime,
    ForeignKey,
    Index,
    LargeBinary,
    MetaData,
    PrimaryKeyConstraint,
    String,
    Text,
    UniqueConstraint,
    func,
    select,
)
from sqlalchemy import Enum as SAEnum
from sqlalchemy import text as sql
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, TSVECTOR
from sqlalchemy.orm import DeclarativeBase, Mapped, column_property, mapped_column, relationship

from kritzellm.api.schemas.blocks import BlockKind
from kritzellm.api.schemas.jobs import JobKind, JobStatus
from kritzellm.api.schemas.pages import PageStatus
from kritzellm.core.embeddings import EMBED_DIMENSIONS
from kritzellm.ids import Prefix, new_id

from .types import TypeId


class Base(DeclarativeBase):
    metadata = MetaData(
        naming_convention={
            "ix": "ix_%(table_name)s_%(column_0_N_name)s",
            "uq": "uq_%(table_name)s_%(column_0_N_name)s",
            "ck": "ck_%(table_name)s_%(constraint_name)s",
            "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
            "pk": "pk_%(table_name)s",
        }
    )
    type_annotation_map = {  # noqa: RUF012
        str: Text(),
        datetime: DateTime(timezone=True),
        dict[str, Any]: JSONB(),
    }


def _id(prefix: Prefix) -> Mapped[str]:
    return mapped_column(TypeId(prefix), primary_key=True, default=lambda: new_id(prefix))


def _enum(enum: type[StrEnum]) -> SAEnum:
    return SAEnum(
        enum,
        native_enum=False,
        values_callable=lambda members: [member.value for member in members],
    )


def _one_of(column: str, enum: type[StrEnum]) -> CheckConstraint:
    values = ", ".join(f"'{member.value}'" for member in enum)
    return CheckConstraint(f"{column} IN ({values})", name=f"{column}_valid")


class Timestamps:
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())


class Page(Timestamps, Base):
    __tablename__ = "pages"
    __table_args__ = (
        UniqueConstraint("journal_id", "sha256"),
        UniqueConstraint("journal_id", "page_number", deferrable=True, initially="DEFERRED"),
        CheckConstraint("page_number >= 1", name="page_number_positive"),
        CheckConstraint("width >= 1 AND height >= 1", name="size_positive"),
        _one_of("status", PageStatus),
    )

    id: Mapped[str] = _id(Prefix.PAGE)
    journal_id: Mapped[str] = mapped_column(
        TypeId(Prefix.JOURNAL), ForeignKey("journals.id", ondelete="CASCADE")
    )
    page_number: Mapped[int]
    page_label: Mapped[str | None] = mapped_column(String(40))
    entry_dates: Mapped[list[date]] = mapped_column(ARRAY(Date), server_default=sql("'{}'"))
    status: Mapped[PageStatus] = mapped_column(
        _enum(PageStatus), server_default=PageStatus.UPLOADED.value
    )
    error: Mapped[dict[str, Any] | None]
    """The RFC 9457 problem that made processing fail."""
    transcription_model: Mapped[str | None]

    original_filename: Mapped[str]
    original_media_type: Mapped[str]
    sha256: Mapped[bytes] = mapped_column(LargeBinary(32))
    """Hash of the uploaded file, to spot re-uploads."""
    width: Mapped[int]
    """Width of the normalized image in pixels."""
    height: Mapped[int]
    """Height of the normalized image in pixels."""

    journal: Mapped[Journal] = relationship(back_populates="pages", lazy="raise")
    blocks: Mapped[list[Block]] = relationship(
        back_populates="page", lazy="raise", passive_deletes=True, order_by="Block.seq"
    )


class Journal(Timestamps, Base):
    __tablename__ = "journals"

    id: Mapped[str] = _id(Prefix.JOURNAL)
    name: Mapped[str] = mapped_column(String(120))
    description: Mapped[str | None]

    page_count: Mapped[int] = column_property(
        select(func.count(Page.id))
        .where(Page.journal_id == id)
        .correlate_except(Page)
        .scalar_subquery()
    )
    """How many pages the journal has, loaded along with it."""

    pages: Mapped[list[Page]] = relationship(
        back_populates="journal", lazy="raise", passive_deletes=True
    )


class Block(Base):
    __tablename__ = "blocks"
    __table_args__ = (
        UniqueConstraint("page_id", "seq", deferrable=True, initially="DEFERRED"),
        CheckConstraint("seq >= 0", name="seq_not_negative"),
        _one_of("kind", BlockKind),
        Index(
            "ix_blocks_text_trgm",
            "text",
            postgresql_using="gin",
            postgresql_ops={"text": "gin_trgm_ops"},
        ),
    )

    id: Mapped[str] = _id(Prefix.BLOCK)
    page_id: Mapped[str] = mapped_column(
        TypeId(Prefix.PAGE), ForeignKey("pages.id", ondelete="CASCADE")
    )
    seq: Mapped[int]
    """Position in reading order, from 0."""
    kind: Mapped[BlockKind] = mapped_column(_enum(BlockKind))
    text: Mapped[str]
    uncertain: Mapped[bool] = mapped_column(server_default=sql("false"))

    page: Mapped[Page] = relationship(back_populates="blocks", lazy="raise")


class Job(Base):
    """Background work. Queued rows are the worker's queue; the API reads them for progress."""

    __tablename__ = "jobs"
    __table_args__ = (
        CheckConstraint("progress_done BETWEEN 0 AND progress_total", name="progress_in_range"),
        _one_of("kind", JobKind),
        _one_of("status", JobStatus),
        CheckConstraint(f"(kind = '{JobKind.REINDEX_ALL}') = (page_id IS NULL)", name="page_given"),
        Index("ix_jobs_queued", "id", postgresql_where=sql("status = 'queued'")),
    )

    id: Mapped[str] = _id(Prefix.JOB)
    """UUIDv7, so ordering by ID is ordering by time (and the queue is first in, first out)."""
    kind: Mapped[JobKind] = mapped_column(_enum(JobKind))
    status: Mapped[JobStatus] = mapped_column(
        _enum(JobStatus), server_default=JobStatus.QUEUED.value
    )
    page_id: Mapped[str | None] = mapped_column(
        TypeId(Prefix.PAGE), ForeignKey("pages.id", ondelete="CASCADE"), index=True
    )
    """The page the job works on, `None` for the whole library. Deleting the page deletes its jobs."""
    progress_done: Mapped[int | None]
    progress_total: Mapped[int | None]
    error: Mapped[dict[str, Any] | None]
    """The RFC 9457 problem that made the job fail."""
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    started_at: Mapped[datetime | None]
    finished_at: Mapped[datetime | None]


TEXT_SEARCH_CONFIG = "simple"
"""Postgres text search configuration for chunks: plain lowercased words, no stemming."""


class Chunk(Base):
    """A run of a page's consecutive blocks, embedded for search. Rebuilt whenever the page is indexed."""

    __tablename__ = "chunks"
    __table_args__ = (
        PrimaryKeyConstraint("page_id", "seq"),
        CheckConstraint("seq >= 0", name="seq_not_negative"),
        Index(
            "ix_chunks_embedding",
            "embedding",
            postgresql_using="hnsw",
            postgresql_ops={"embedding": "vector_cosine_ops"},
        ),
        Index("ix_chunks_tsv", "tsv", postgresql_using="gin"),
    )

    page_id: Mapped[str] = mapped_column(
        TypeId(Prefix.PAGE), ForeignKey("pages.id", ondelete="CASCADE")
    )
    seq: Mapped[int]
    """Position on the page, from 0."""
    block_ids: Mapped[list[str]] = mapped_column(ARRAY(TypeId(Prefix.BLOCK)))
    """The blocks the text comes from, in order. A long block can be spread over several chunks."""
    text: Mapped[str]
    embedding: Mapped[list[float]] = mapped_column(Vector(EMBED_DIMENSIONS))
    embed_model: Mapped[str]
    """Model that made `embedding`."""
    tsv: Mapped[str] = mapped_column(
        TSVECTOR, Computed(f"to_tsvector('{TEXT_SEARCH_CONFIG}', text)", persisted=True)
    )
    """The words of `text`, for full-text search."""
