"""message tool calls and sources

Created: 2026-11-27 20:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "7b574ce89f49"
down_revision: str | Sequence[str] | None = "e6103435e4fa"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    for column in ("tool_calls", "sources"):
        op.add_column(
            "messages",
            sa.Column(
                column,
                postgresql.JSONB(astext_type=sa.Text()),
                server_default=sa.text("'[]'"),
                nullable=False,
            ),
        )


def downgrade() -> None:
    op.drop_column("messages", "sources")
    op.drop_column("messages", "tool_calls")
