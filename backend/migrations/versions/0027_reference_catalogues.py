"""Five space reference tables and immutable v1 fixture snapshots."""

import json
from importlib.resources import files
from pathlib import Path
from uuid import UUID

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "0027"
down_revision = "0026"
TABLES = (
    ("biological-sex", "reference_biological_sex"),
    ("genders", "reference_genders"),
    ("practices", "reference_practices"),
    ("timezones", "reference_timezones"),
    ("relationship-types", "reference_relationship_types"),
)


def upgrade():
    for kind, name in TABLES:
        table = op.create_table(
            name,
            sa.Column("uid", sa.UUID(), primary_key=True),
            sa.Column("name", sa.Text(), nullable=False),
            sa.Column("description", sa.Text(), nullable=False, server_default=""),
            sa.Column("icon", sa.Text(), nullable=True),
            sa.Column("extra", JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
            sa.CheckConstraint("length(btrim(name)) > 0"),
        )
        op.create_index(name + "_name_unique", name, [sa.func.lower(table.c.name)], unique=True)
        source = files("vowen.modules.references").joinpath("fixtures/v1", kind + ".json")
        if kind == "timezones":
            source = Path(__file__).resolve().parents[1] / "fixtures/0027-timezones.json"
        rows = json.loads(source.read_text(encoding="utf-8"))
        for row in rows:
            row["uid"] = UUID(row["uid"])
        op.bulk_insert(table, rows)


def downgrade():
    for _, name in reversed(TABLES):
        op.drop_table(name)
