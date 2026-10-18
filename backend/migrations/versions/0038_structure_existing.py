"""Structure fixation devices and care practices without new catalogues or records."""

import json
from pathlib import Path
from uuid import UUID

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "0038"
down_revision = "0037"
TABLES = {
    "devices": "reference_devices",
    "practices": "reference_practices",
    "practice-categories": "reference_practice_categories",
}


def apply(connection, reverse=False):
    changes = json.loads(
        (
            Path(__file__).resolve().parents[1] / "fixtures" / "0038-structure-existing.json"
        ).read_text("utf-8")
    )
    for change in changes:
        before, after = change["before"], change["after"]
        if reverse:
            before, after = after, before
        for row in (before, after):
            row["uid"] = UUID(row["uid"])
            if row.get("category_uid"):
                row["category_uid"] = UUID(row["category_uid"])
        columns = [
            sa.column("uid", sa.UUID()),
            sa.column("name", sa.Text()),
            sa.column("description", sa.Text()),
            sa.column("icon", sa.Text()),
            sa.column("url", sa.Text()),
            sa.column("extra", JSONB()),
        ]
        if change["kind"] == "practices":
            columns.append(sa.column("category_uid", sa.UUID()))
        target = sa.table(TABLES[change["kind"]], *columns)
        # Exact fixture match only: preserve personal edits, stable IDs and M:N links.
        connection.execute(
            sa.update(target)
            .where(
                sa.and_(
                    *(target.c[key].is_not_distinct_from(value) for key, value in before.items())
                )
            )
            .values(after)
        )


def upgrade():
    apply(op.get_bind())


def downgrade():
    apply(op.get_bind(), reverse=True)
