"""Neutral health condition and allergen reference catalogues."""

import json
from pathlib import Path
from uuid import UUID

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "0037"
down_revision = "0036"
TABLES = {
    "health-conditions": "reference_health_conditions",
    "allergens": "reference_allergens",
}


def upgrade():
    for kind, name in TABLES.items():
        target = op.create_table(
            name,
            sa.Column("uid", sa.UUID(), primary_key=True),
            sa.Column("name", sa.Text(), nullable=False),
            sa.Column("description", sa.Text(), nullable=False, server_default=""),
            sa.Column("icon", sa.Text(), nullable=True),
            sa.Column("url", sa.Text(), nullable=True),
            sa.Column("extra", JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
            sa.CheckConstraint("length(btrim(name)) > 0"),
        )
        op.create_index(name + "_name_unique", name, [sa.text("lower(name)")], unique=True)
        rows = json.loads(
            (Path(__file__).resolve().parents[1] / "fixtures" / f"0037-{kind}.json").read_text(
                "utf-8"
            )
        )
        for row in rows:
            row["uid"] = UUID(row["uid"])
        op.bulk_insert(target, rows)


def downgrade():
    for name in reversed(TABLES.values()):
        op.drop_table(name)
