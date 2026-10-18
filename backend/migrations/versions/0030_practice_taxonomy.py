"""Replace generic activity fixtures with sexual and BDSM practice terminology."""

import json
from pathlib import Path
from uuid import UUID

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, insert

revision = "0030"
down_revision = "0029"

practices = sa.table(
    "reference_practices",
    sa.column("uid", sa.UUID()),
    sa.column("name", sa.Text()),
    sa.column("description", sa.Text()),
    sa.column("icon", sa.Text()),
    sa.column("url", sa.Text()),
    sa.column("extra", JSONB()),
)


def rows(filename):
    result = json.loads(
        (Path(__file__).resolve().parents[1] / "fixtures" / filename).read_text("utf-8")
    )
    for row in result:
        row["uid"] = UUID(row["uid"])
    return result


def replace_unchanged(source, target):
    connection = op.get_bind()
    targets = {row["uid"]: row for row in target}
    for row in source:
        # Preserve user modifications, links and additions; only replace exact seed data.
        match = sa.and_(
            *(practices.c[key].is_not_distinct_from(value) for key, value in row.items())
        )
        if row["uid"] in targets:
            connection.execute(sa.update(practices).where(match).values(targets[row["uid"]]))
        else:
            connection.execute(sa.delete(practices).where(match))
    connection.execute(insert(practices).values(target).on_conflict_do_nothing())


def upgrade():
    replace_unchanged(rows("0029-practices.json"), rows("0030-practices.json"))


def downgrade():
    replace_unchanged(rows("0030-practices.json"), rows("0029-practices.json"))
