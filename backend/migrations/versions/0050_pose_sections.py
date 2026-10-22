"""Add remaining pose sections and explicit equipment/composition links."""

import json
from pathlib import Path
from uuid import UUID

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, insert

revision = "0050"
down_revision = "0049"


def apply(connection: sa.Connection, reverse: bool = False) -> None:
    snapshot = json.loads(
        (Path(__file__).resolve().parents[1] / "fixtures/0050-pose-sections.json").read_text(
            "utf-8"
        )
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
    for kind, name, field in (
        ("pose-devices", "reference_pose_devices", "device_uid"),
        ("pose-compositions", "reference_pose_compositions", "composition_uid"),
    ):
        targets[kind] = sa.table(
            name, sa.column("pose_uid", sa.UUID()), sa.column(field, sa.UUID())
        )
    for rows in snapshot.values():
        for row in rows:
            for key in ("uid", "category_uid", "pose_uid", "device_uid", "composition_uid"):
                if key in row:
                    row[key] = UUID(row[key])
    if not reverse:
        for kind, target in targets.items():
            connection.execute(insert(target).values(snapshot[kind]).on_conflict_do_nothing())
        return
    for kind in ("pose-devices", "pose-compositions", "poses", "pose-categories"):
        target = targets[kind]
        for row in snapshot[kind]:
            conditions = [target.c[key].is_not_distinct_from(value) for key, value in row.items()]
            if kind == "poses":
                for link in (targets["pose-devices"], targets["pose-compositions"]):
                    conditions.append(~sa.exists().where(link.c.pose_uid == target.c.uid))
            if kind == "pose-categories":
                conditions.append(
                    ~sa.exists().where(targets["poses"].c.category_uid == target.c.uid)
                )
            connection.execute(sa.delete(target).where(*conditions))


def upgrade() -> None:
    for table, column, reference in (
        ("reference_pose_devices", "device_uid", "reference_devices"),
        ("reference_pose_compositions", "composition_uid", "reference_participant_compositions"),
    ):
        op.create_table(
            table,
            sa.Column(
                "pose_uid",
                sa.UUID(),
                sa.ForeignKey("reference_poses.uid", ondelete="CASCADE"),
                primary_key=True,
            ),
            sa.Column(
                column,
                sa.UUID(),
                sa.ForeignKey(reference + ".uid", ondelete="RESTRICT"),
                primary_key=True,
            ),
        )
        op.create_index("ix_" + table + "_" + column, table, [column])
    apply(op.get_bind())


def downgrade() -> None:
    apply(op.get_bind(), reverse=True)
    op.drop_table("reference_pose_compositions")
    op.drop_table("reference_pose_devices")
