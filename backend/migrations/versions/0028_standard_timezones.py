"""Limit seeded timezones to the selected 24 standard regional zones."""

import json
from pathlib import Path
from uuid import UUID

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, insert

revision = "0028"
down_revision = "0027"

zones = sa.table(
    "reference_timezones",
    sa.column("uid", sa.UUID()),
    sa.column("name", sa.Text()),
    sa.column("description", sa.Text()),
    sa.column("icon", sa.Text()),
    sa.column("extra", JSONB()),
)


def rows(filename):
    result = json.loads(
        (Path(__file__).resolve().parents[1] / "fixtures" / filename).read_text(encoding="utf-8")
    )
    for row in result:
        row["uid"] = UUID(row["uid"])
    return result


def upgrade():
    selected = rows("0028-timezones.json")
    keep = {row["uid"] for row in selected}
    retired = [row["uid"] for row in rows("0027-timezones.json") if row["uid"] not in keep]
    # Remove only known seeded UUIDs, never unrelated custom entries or profile timezone strings.
    op.get_bind().execute(sa.delete(zones).where(zones.c.uid.in_(retired)))
    op.get_bind().execute(insert(zones).values(selected).on_conflict_do_nothing())


def downgrade():
    op.get_bind().execute(
        insert(zones).values(rows("0027-timezones.json")).on_conflict_do_nothing()
    )
