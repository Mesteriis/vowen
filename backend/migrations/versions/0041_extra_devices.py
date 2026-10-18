"""Add machine and equipment reference fixtures while preserving local edits."""

import json
from pathlib import Path
from uuid import UUID

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, insert

revision = "0041"
down_revision = "0040"


def apply(connection: sa.Connection, reverse: bool = False) -> None:
    rows = json.loads(
        (Path(__file__).resolve().parents[1] / "fixtures" / "0041-extra-devices.json").read_text(
            "utf-8"
        )
    )
    for row in rows:
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
    if not reverse:
        # Both UID and case-insensitive name conflicts preserve the existing record.
        connection.execute(insert(target).values(rows).on_conflict_do_nothing())
        return
    links = sa.table("reference_practice_devices", sa.column("device_uid", sa.UUID()))
    for row in rows:
        # A downgrade must not remove edits or break a user's equipment links.
        connection.execute(
            sa.delete(target).where(
                *(target.c[key].is_not_distinct_from(value) for key, value in row.items()),
                ~sa.exists().where(links.c.device_uid == target.c.uid),
            )
        )


def upgrade() -> None:
    apply(op.get_bind())


def downgrade() -> None:
    apply(op.get_bind(), reverse=True)
