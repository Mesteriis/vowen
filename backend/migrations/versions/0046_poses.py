"""Pose categories and poses with explicit category foreign keys and frozen fixtures."""

import json
from pathlib import Path
from uuid import UUID

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "0046"
down_revision = "0045"


def upgrade() -> None:
    snapshot = json.loads(
        (Path(__file__).resolve().parents[1] / "fixtures/0046-poses.json").read_text("utf-8")
    )
    for kind, name in (
        ("pose-categories", "reference_pose_categories"),
        ("poses", "reference_poses"),
    ):
        category = (
            [
                sa.Column(
                    "category_uid",
                    sa.UUID(),
                    sa.ForeignKey("reference_pose_categories.uid", ondelete="RESTRICT"),
                    nullable=False,
                )
            ]
            if kind == "poses"
            else []
        )
        table = op.create_table(
            name,
            sa.Column("uid", sa.UUID(), primary_key=True),
            sa.Column("name", sa.Text(), nullable=False),
            sa.Column("description", sa.Text(), nullable=False, server_default=""),
            sa.Column("icon", sa.Text(), nullable=True),
            sa.Column("thumbnail", sa.Text(), nullable=True),
            sa.Column("url", sa.Text(), nullable=True),
            sa.Column("extra", JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
            *category,
            sa.CheckConstraint("length(btrim(name)) > 0"),
        )
        op.create_index(name + "_name_unique", name, [sa.func.lower(table.c.name)], unique=True)
        if kind == "poses":
            op.create_index("ix_reference_poses_category_uid", name, ["category_uid"])
        rows = snapshot[kind]
        for row in rows:
            row["uid"] = UUID(row["uid"])
            if "category_uid" in row:
                row["category_uid"] = UUID(row["category_uid"])
        op.bulk_insert(table, rows)


def downgrade() -> None:
    op.drop_table("reference_poses")
    op.drop_table("reference_pose_categories")
