"""Consolidate machine variants and add reference toys without replacing user edits."""

import json
from pathlib import Path
from typing import Any
from uuid import UUID

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, insert

revision = "0042"
down_revision = "0041"


def apply(connection: sa.Connection, reverse: bool = False) -> None:
    data = json.loads(
        (
            Path(__file__).resolve().parents[1] / "fixtures" / "0042-simplify-machines-toys.json"
        ).read_text("utf-8")
    )
    for row in [data["old_canonical"], data["canonical"], *data["removed"], *data["added"]]:
        row["uid"] = UUID(row["uid"])
    target = sa.table(
        "reference_devices",
        sa.column("uid", sa.UUID()),
        sa.column("name", sa.Text()),
        sa.column("description", sa.Text()),
        sa.column("icon", sa.Text()),
        sa.column("thumbnail", sa.Text()),
        sa.column("url", sa.Text()),
        sa.column("extra", JSONB()),
    )
    links = sa.table(
        "reference_practice_devices",
        sa.column("practice_uid", sa.UUID()),
        sa.column("device_uid", sa.UUID()),
    )

    def exact(row: dict[str, Any]) -> sa.ColumnElement[bool]:
        return sa.and_(*(target.c[key].is_not_distinct_from(value) for key, value in row.items()))

    old, new = data["old_canonical"], data["canonical"]
    source, destination = (new, old) if reverse else (old, new)
    other = target.alias("other_device")
    connection.execute(
        sa.update(target)
        .where(
            exact(source),
            ~sa.exists().where(
                other.c.uid != source["uid"],
                sa.func.lower(other.c.name) == destination["name"].lower(),
            ),
        )
        .values(**destination)
    )
    if reverse:
        connection.execute(insert(target).values(data["removed"]).on_conflict_do_nothing())
        for row in data["added"]:
            connection.execute(
                sa.delete(target).where(
                    exact(row), ~sa.exists().where(links.c.device_uid == target.c.uid)
                )
            )
        # Links consolidated by upgrade stay on the canonical concept on downgrade.
        return
    connection.execute(insert(target).values(data["added"]).on_conflict_do_nothing())
    if connection.scalar(sa.select(target.c.uid).where(target.c.uid == new["uid"])) is None:
        return
    for row in data["removed"]:
        # Lock before checking, moving links and deleting to serialize with FK writes.
        existing = connection.execute(
            sa.select(target.c.uid).where(exact(row)).with_for_update()
        ).scalar_one_or_none()
        if existing is None:
            continue
        connection.execute(
            insert(links)
            .from_select(
                ["practice_uid", "device_uid"],
                sa.select(links.c.practice_uid, sa.literal(new["uid"], type_=sa.UUID())).where(
                    links.c.device_uid == row["uid"]
                ),
            )
            .on_conflict_do_nothing()
        )
        connection.execute(sa.delete(links).where(links.c.device_uid == row["uid"]))
        connection.execute(sa.delete(target).where(exact(row)))


def upgrade() -> None:
    apply(op.get_bind())


def downgrade() -> None:
    apply(op.get_bind(), reverse=True)
