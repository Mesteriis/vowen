"""Add nullable reference links and expand the practice fixtures to 100."""

import json
from pathlib import Path
from uuid import UUID

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, insert

revision = "0029"
down_revision = "0028"

TABLES = (
    "reference_biological_sex",
    "reference_genders",
    "reference_practices",
    "reference_timezones",
    "reference_relationship_types",
)


def upgrade():
    for table in TABLES:
        op.add_column(table, sa.Column("url", sa.Text(), nullable=True))
    practices = sa.table(
        "reference_practices",
        sa.column("uid", sa.UUID()),
        sa.column("name", sa.Text()),
        sa.column("description", sa.Text()),
        sa.column("icon", sa.Text()),
        sa.column("url", sa.Text()),
        sa.column("extra", JSONB()),
    )
    rows = json.loads(
        (Path(__file__).resolve().parents[1] / "fixtures/0029-practices.json").read_text(
            encoding="utf-8"
        )
    )
    for row in rows:
        row["uid"] = UUID(row["uid"])
    op.get_bind().execute(insert(practices).values(rows).on_conflict_do_nothing())


def downgrade():
    # Keep seeded and custom practices: rolling schema back must not remove catalogue records.
    for table in reversed(TABLES):
        op.drop_column(table, "url")
