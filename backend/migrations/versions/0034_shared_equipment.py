"""Shared equipment/body catalogues and explicit many-to-many practice links."""

import json
from pathlib import Path
from uuid import UUID

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, insert

revision = "0034"
down_revision = "0033"


def rows(kind):
    data = json.loads(
        (Path(__file__).resolve().parents[1] / "fixtures" / f"0034-{kind}.json").read_text("utf-8")
    )
    for row in data:
        for key in row:
            if key == "uid" or key.endswith("_uid"):
                row[key] = UUID(row[key])
    return data


def upgrade():
    for name, kind in (("reference_devices", "devices"), ("reference_body_parts", "body-parts")):
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
        op.bulk_insert(target, rows(kind))
    for name, kind, field, parent in (
        ("reference_practice_devices", "practice-devices", "device_uid", "reference_devices"),
        (
            "reference_practice_body_parts",
            "practice-body-parts",
            "body_part_uid",
            "reference_body_parts",
        ),
    ):
        target = op.create_table(
            name,
            sa.Column(
                "practice_uid",
                sa.UUID(),
                sa.ForeignKey("reference_practices.uid", ondelete="CASCADE"),
                primary_key=True,
            ),
            sa.Column(
                field,
                sa.UUID(),
                sa.ForeignKey(parent + ".uid", ondelete="RESTRICT"),
                primary_key=True,
            ),
        )
        op.create_index("ix_" + name + "_" + field, name, [field])
        # A locally removed practice need not be recreated solely for a link.
        practices = sa.table("reference_practices", sa.column("uid", sa.UUID()))
        existing = set(op.get_bind().scalars(sa.select(practices.c.uid)))
        available = [row for row in rows(kind) if row["practice_uid"] in existing]
        if available:
            op.get_bind().execute(insert(target).values(available).on_conflict_do_nothing())


def downgrade():
    op.drop_table("reference_practice_body_parts")
    op.drop_table("reference_practice_devices")
    op.drop_table("reference_body_parts")
    op.drop_table("reference_devices")
