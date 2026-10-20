"""initial schema

Created: 2026-10-20 22:47:22.279476
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "37c8472ca615"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "journals",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_journals")),
    )
    op.create_table(
        "pages",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("journal_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("page_number", sa.Integer(), nullable=False),
        sa.Column("page_label", sa.String(length=40), nullable=True),
        sa.Column(
            "entry_dates",
            postgresql.ARRAY(sa.Date()),
            server_default=sa.text("'{}'"),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.Enum(
                "uploaded",
                "transcribing",
                "indexing",
                "ready",
                "failed",
                name="pagestatus",
                native_enum=False,
            ),
            server_default="uploaded",
            nullable=False,
        ),
        sa.Column("error", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("transcription_model", sa.Text(), nullable=True),
        sa.Column("original_filename", sa.Text(), nullable=False),
        sa.Column("original_media_type", sa.Text(), nullable=False),
        sa.Column("sha256", sa.LargeBinary(length=32), nullable=False),
        sa.Column("width", sa.Integer(), nullable=False),
        sa.Column("height", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "status IN ('uploaded', 'transcribing', 'indexing', 'ready', 'failed')",
            name=op.f("ck_pages_status_valid"),
        ),
        sa.CheckConstraint("page_number >= 1", name=op.f("ck_pages_page_number_positive")),
        sa.CheckConstraint("width >= 1 AND height >= 1", name=op.f("ck_pages_size_positive")),
        sa.ForeignKeyConstraint(
            ["journal_id"],
            ["journals.id"],
            name=op.f("fk_pages_journal_id_journals"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_pages")),
        sa.UniqueConstraint(
            "journal_id",
            "page_number",
            deferrable=True,
            initially="DEFERRED",
            name=op.f("uq_pages_journal_id_page_number"),
        ),
        sa.UniqueConstraint("journal_id", "sha256", name=op.f("uq_pages_journal_id_sha256")),
    )
    op.create_table(
        "blocks",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("page_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("seq", sa.Integer(), nullable=False),
        sa.Column(
            "kind",
            sa.Enum(
                "heading",
                "paragraph",
                "list",
                "marginNote",
                "drawing",
                "other",
                name="blockkind",
                native_enum=False,
            ),
            nullable=False,
        ),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("uncertain", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.CheckConstraint(
            "kind IN ('heading', 'paragraph', 'list', 'marginNote', 'drawing', 'other')",
            name=op.f("ck_blocks_kind_valid"),
        ),
        sa.CheckConstraint("seq >= 0", name=op.f("ck_blocks_seq_not_negative")),
        sa.ForeignKeyConstraint(
            ["page_id"], ["pages.id"], name=op.f("fk_blocks_page_id_pages"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_blocks")),
        sa.UniqueConstraint(
            "page_id",
            "seq",
            deferrable=True,
            initially="DEFERRED",
            name=op.f("uq_blocks_page_id_seq"),
        ),
    )
    op.create_table(
        "jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "kind",
            sa.Enum(
                "ingestPage", "transcribePage", "reindexPage", name="jobkind", native_enum=False
            ),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.Enum(
                "queued", "running", "succeeded", "failed", name="jobstatus", native_enum=False
            ),
            server_default="queued",
            nullable=False,
        ),
        sa.Column("page_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("progress_done", sa.Integer(), nullable=True),
        sa.Column("progress_total", sa.Integer(), nullable=True),
        sa.Column("error", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "kind IN ('ingestPage', 'transcribePage', 'reindexPage')",
            name=op.f("ck_jobs_kind_valid"),
        ),
        sa.CheckConstraint(
            "status IN ('queued', 'running', 'succeeded', 'failed')",
            name=op.f("ck_jobs_status_valid"),
        ),
        sa.CheckConstraint(
            "progress_done BETWEEN 0 AND progress_total", name=op.f("ck_jobs_progress_in_range")
        ),
        sa.ForeignKeyConstraint(
            ["page_id"], ["pages.id"], name=op.f("fk_jobs_page_id_pages"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_jobs")),
    )
    op.create_index(op.f("ix_jobs_page_id"), "jobs", ["page_id"], unique=False)
    op.create_index(
        "ix_jobs_queued",
        "jobs",
        ["id"],
        unique=False,
        postgresql_where=sa.text("status = 'queued'"),
    )


def downgrade() -> None:
    op.drop_index(
        "ix_jobs_queued", table_name="jobs", postgresql_where=sa.text("status = 'queued'")
    )
    op.drop_index(op.f("ix_jobs_page_id"), table_name="jobs")
    op.drop_table("jobs")
    op.drop_table("blocks")
    op.drop_table("pages")
    op.drop_table("journals")
