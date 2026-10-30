"""chunks and embeddings

Created: 2026-10-31 12:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects import postgresql

revision: str = "f6e6c524ee26"
down_revision: str | Sequence[str] | None = "37c8472ca615"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

PAGE_KINDS = "'ingestPage', 'transcribePage', 'reindexPage'"


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.create_table(
        "chunks",
        sa.Column("page_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("seq", sa.Integer(), nullable=False),
        sa.Column("block_ids", postgresql.ARRAY(postgresql.UUID(as_uuid=True)), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("embedding", Vector(1536), nullable=False),
        sa.Column("embed_model", sa.Text(), nullable=False),
        sa.CheckConstraint("seq >= 0", name=op.f("ck_chunks_seq_not_negative")),
        sa.ForeignKeyConstraint(
            ["page_id"], ["pages.id"], name=op.f("fk_chunks_page_id_pages"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("page_id", "seq", name=op.f("pk_chunks")),
    )

    op.alter_column("jobs", "page_id", existing_type=postgresql.UUID(as_uuid=True), nullable=True)
    op.drop_constraint(op.f("ck_jobs_kind_valid"), "jobs", type_="check")
    op.create_check_constraint(
        op.f("ck_jobs_kind_valid"), "jobs", f"kind IN ({PAGE_KINDS}, 'reindexAll')"
    )
    op.create_check_constraint(
        op.f("ck_jobs_page_given"), "jobs", "(kind = 'reindexAll') = (page_id IS NULL)"
    )


def downgrade() -> None:
    op.execute("DELETE FROM jobs WHERE kind = 'reindexAll'")
    op.drop_constraint(op.f("ck_jobs_page_given"), "jobs", type_="check")
    op.drop_constraint(op.f("ck_jobs_kind_valid"), "jobs", type_="check")
    op.create_check_constraint(op.f("ck_jobs_kind_valid"), "jobs", f"kind IN ({PAGE_KINDS})")
    op.alter_column("jobs", "page_id", existing_type=postgresql.UUID(as_uuid=True), nullable=False)

    op.drop_table("chunks")
    op.execute("DROP EXTENSION IF EXISTS vector")
