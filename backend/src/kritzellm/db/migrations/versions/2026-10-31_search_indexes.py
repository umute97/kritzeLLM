"""search indexes

Created: 2026-10-31 09:17:28.672672
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "a0d28dd6e77f"
down_revision: str | Sequence[str] | None = "f6e6c524ee26"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
    op.create_index(
        "ix_blocks_text_trgm",
        "blocks",
        ["text"],
        postgresql_using="gin",
        postgresql_ops={"text": "gin_trgm_ops"},
    )

    op.add_column(
        "chunks",
        sa.Column(
            "tsv",
            postgresql.TSVECTOR(),
            sa.Computed("to_tsvector('simple', text)", persisted=True),
            nullable=False,
        ),
    )
    op.create_index("ix_chunks_tsv", "chunks", ["tsv"], postgresql_using="gin")
    op.create_index(
        "ix_chunks_embedding",
        "chunks",
        ["embedding"],
        postgresql_using="hnsw",
        postgresql_ops={"embedding": "vector_cosine_ops"},
    )


def downgrade() -> None:
    op.drop_index("ix_chunks_embedding", table_name="chunks")
    op.drop_index("ix_chunks_tsv", table_name="chunks")
    op.drop_column("chunks", "tsv")

    op.drop_index("ix_blocks_text_trgm", table_name="blocks")
    op.execute("DROP EXTENSION IF EXISTS pg_trgm")
