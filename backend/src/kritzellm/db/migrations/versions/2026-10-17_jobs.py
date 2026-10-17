"""jobs

Created: 2026-10-17 16:31:53.794479
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "b8ab10802c0d"
down_revision: str | Sequence[str] | None = "0848061d24cd"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "kind",
            sa.Enum(
                "ingestPage",
                "transcribePage",
                "reindexPage",
                "reindexAll",
                "exportJournal",
                name="jobkind",
                native_enum=False,
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
        sa.Column("page_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("journal_id", postgresql.UUID(as_uuid=True), nullable=True),
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
            "kind IN ('ingestPage', 'transcribePage', 'reindexPage', 'reindexAll', 'exportJournal')",
            name=op.f("ck_jobs_kind_valid"),
        ),
        sa.CheckConstraint(
            "status IN ('queued', 'running', 'succeeded', 'failed')",
            name=op.f("ck_jobs_status_valid"),
        ),
        sa.CheckConstraint(
            "page_id IS NULL OR journal_id IS NULL", name=op.f("ck_jobs_one_target")
        ),
        sa.CheckConstraint(
            "progress_done BETWEEN 0 AND progress_total", name=op.f("ck_jobs_progress_in_range")
        ),
        sa.ForeignKeyConstraint(
            ["journal_id"],
            ["journals.id"],
            name=op.f("fk_jobs_journal_id_journals"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["page_id"], ["pages.id"], name=op.f("fk_jobs_page_id_pages"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_jobs")),
    )
    op.create_index(
        op.f("ix_jobs_queued"),
        "jobs",
        ["id"],
        unique=False,
        postgresql_where=sa.text("status = 'queued'"),
    )
    op.create_index(op.f("ix_jobs_journal_id"), "jobs", ["journal_id"], unique=False)
    op.create_index(op.f("ix_jobs_page_id"), "jobs", ["page_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_jobs_page_id"), table_name="jobs")
    op.drop_index(op.f("ix_jobs_journal_id"), table_name="jobs")
    op.drop_index(
        op.f("ix_jobs_queued"), table_name="jobs", postgresql_where=sa.text("status = 'queued'")
    )
    op.drop_table("jobs")
