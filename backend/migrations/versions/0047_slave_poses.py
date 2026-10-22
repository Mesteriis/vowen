"""Add source-described protocol poses without images, preserving local edits."""

import json
from pathlib import Path
from uuid import UUID

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, insert

revision = "0047"
down_revision = "0046"


def apply(connection: sa.Connection, reverse: bool = False) -> None:
    snapshot = json.loads(
        (Path(__file__).resolve().parents[1] / "fixtures/0047-slave-poses.json").read_text("utf-8")
    )
    targets = {}
    for kind, name in (
        ("pose-categories", "reference_pose_categories"),
        ("poses", "reference_poses"),
    ):
        columns = [
            sa.column("uid", sa.UUID()),
            sa.column("name", sa.Text()),
            sa.column("description", sa.Text()),
            sa.column("icon", sa.Text()),
            sa.column("thumbnail", sa.Text()),
            sa.column("url", sa.Text()),
            sa.column("extra", JSONB()),
        ]
        if kind == "poses":
            columns.append(sa.column("category_uid", sa.UUID()))
        targets[kind] = sa.table(name, *columns)
        for row in snapshot[kind]:
            row["uid"] = UUID(row["uid"])
            if "category_uid" in row:
                row["category_uid"] = UUID(row["category_uid"])
    if not reverse:
        for kind, target in targets.items():
            connection.execute(insert(target).values(snapshot[kind]).on_conflict_do_nothing())
        return
    for kind in ("poses", "pose-categories"):
        target = targets[kind]
        for row in snapshot[kind]:
            conditions = [target.c[key].is_not_distinct_from(value) for key, value in row.items()]
            if kind == "pose-categories":
                conditions.append(
                    ~sa.exists().where(targets["poses"].c.category_uid == target.c.uid)
                )
            connection.execute(sa.delete(target).where(*conditions))


def upgrade() -> None:
    apply(op.get_bind())


def downgrade() -> None:
    apply(op.get_bind(), reverse=True)
