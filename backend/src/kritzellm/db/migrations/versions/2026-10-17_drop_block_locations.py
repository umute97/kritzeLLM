"""drop block locations

Sources cite the page, not a spot on it, so blocks no longer store bands, side or box.

Created: 2026-10-17 18:12:04.512937
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "7db6683576c3"
down_revision: str | Sequence[str] | None = "b8ab10802c0d"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

COLUMNS = [
    "band_start",
    "band_end",
    "band_total",
    "side",
    "box_x",
    "box_y",
    "box_width",
    "box_height",
]
CONSTRAINTS = ["ck_blocks_side_valid", "ck_blocks_bands_in_order", "ck_blocks_box_normalized"]


def upgrade() -> None:
    for name in CONSTRAINTS:
        op.drop_constraint(op.f(name), "blocks", type_="check")
    for name in COLUMNS:
        op.drop_column("blocks", name)


# Old blocks come back located on the whole page: band 1 of 1, both sides, the full box.
WHOLE_PAGE = {
    "band_start": "1",
    "band_end": "1",
    "band_total": "1",
    "side": "full",
    "box_x": "0",
    "box_y": "0",
    "box_width": "1",
    "box_height": "1",
}


def downgrade() -> None:
    types = {
        "band_start": sa.Integer(),
        "band_end": sa.Integer(),
        "band_total": sa.Integer(),
        "side": sa.Enum("left", "right", "full", name="side", native_enum=False),
        "box_x": sa.REAL(),
        "box_y": sa.REAL(),
        "box_width": sa.REAL(),
        "box_height": sa.REAL(),
    }
    for name in COLUMNS:
        column = sa.Column(name, types[name], nullable=False, server_default=WHOLE_PAGE[name])
        op.add_column("blocks", column)
        op.alter_column("blocks", name, server_default=None)
    op.create_check_constraint(
        op.f("ck_blocks_side_valid"), "blocks", "side IN ('left', 'right', 'full')"
    )
    op.create_check_constraint(
        op.f("ck_blocks_bands_in_order"),
        "blocks",
        "1 <= band_start AND band_start <= band_end AND band_end <= band_total",
    )
    op.create_check_constraint(
        op.f("ck_blocks_box_normalized"),
        "blocks",
        "box_x BETWEEN 0 AND 1 AND box_y BETWEEN 0 AND 1"
        " AND box_width BETWEEN 0 AND 1 AND box_height BETWEEN 0 AND 1",
    )
