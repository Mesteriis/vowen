"""Expand modern editorial selection to 64 poses without duplicating existing IDs."""

import json
from pathlib import Path
from uuid import UUID

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, insert

revision = "0048"
down_revision = "0047"


def apply(connection: sa.Connection, reverse: bool = False) -> None:
    snapshot = json.loads(
        (Path(__file__).resolve().parents[1] / "fixtures/0048-modern-poses.json").read_text("utf-8")
    )
    target = sa.table(
        "reference_poses",
        sa.column("uid", sa.UUID()),
        sa.column("name", sa.Text()),
        sa.column("description", sa.Text()),
        sa.column("icon", sa.Text()),
        sa.column("thumbnail", sa.Text()),
        sa.column("url", sa.Text()),
        sa.column("extra", JSONB()),
        sa.column("category_uid", sa.UUID()),
    )
    rows = snapshot["poses"]
    for row in rows:
        row["uid"] = UUID(row["uid"])
        row["category_uid"] = UUID(row["category_uid"])
    existing = [UUID(uid) for uid in snapshot["existing_pose_uids"]]
    collection = {"collections": ["modern-64"]}
    if not reverse:
        connection.execute(insert(target).values(rows).on_conflict_do_nothing())
        # Add only absent metadata. Names, descriptions and custom tags are untouched.
        connection.execute(
            target.update()
            .where(target.c.uid.in_(existing), ~target.c.extra.op("?")("collections"))
            .values(extra=target.c.extra.op("||")(sa.cast(collection, JSONB())))
        )
        return
    for row in rows:
        connection.execute(
            sa.delete(target).where(
                *(target.c[key].is_not_distinct_from(value) for key, value in row.items())
            )
        )
    connection.execute(
        target.update()
        .where(
            target.c.uid.in_(existing),
            target.c.extra["collections"] == sa.cast(["modern-64"], JSONB()),
        )
        .values(extra=target.c.extra.op("-")("collections"))
    )


def upgrade() -> None:
    apply(op.get_bind())


def downgrade() -> None:
    apply(op.get_bind(), reverse=True)
