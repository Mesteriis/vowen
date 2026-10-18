"""Refine practice categories and consolidate contextual variants into aliases."""

import json
from pathlib import Path
from uuid import UUID

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, insert

revision = "0032"
down_revision = "0031"


def table(name, practice=False):
    columns = [
        sa.column("uid", sa.UUID()),
        sa.column("name", sa.Text()),
        sa.column("description", sa.Text()),
        sa.column("icon", sa.Text()),
        sa.column("url", sa.Text()),
        sa.column("extra", JSONB()),
    ]
    if practice:
        columns.append(sa.column("category_uid", sa.UUID()))
    return sa.table(name, *columns)


categories = table("reference_practice_categories")
practices = table("reference_practices", True)


def rows(version, kind):
    result = json.loads(
        (Path(__file__).resolve().parents[1] / "fixtures" / f"{version}-{kind}.json").read_text(
            "utf-8"
        )
    )
    for row in result:
        row["uid"] = UUID(row["uid"])
        if row.get("category_uid"):
            row["category_uid"] = UUID(row["category_uid"])
    return result


def unchanged(target, row):
    return sa.and_(*(target.c[key].is_not_distinct_from(value) for key, value in row.items()))


def transition(connection, source, destination):
    old_categories = rows(source, "practice-categories")
    new_categories = rows(destination, "practice-categories")
    desired_categories = {row["uid"]: row for row in new_categories}
    for row in old_categories:
        if row["uid"] in desired_categories:
            connection.execute(
                sa.update(categories)
                .where(unchanged(categories, row))
                .values(desired_categories[row["uid"]])
            )
    connection.execute(insert(categories).values(new_categories).on_conflict_do_nothing())
    old_practices = rows(source, "practices")
    new_practices = rows(destination, "practices")
    desired_practices = {row["uid"]: row for row in new_practices}
    for row in old_practices:
        match = unchanged(practices, row)
        if row["uid"] in desired_practices:
            connection.execute(
                sa.update(practices).where(match).values(desired_practices[row["uid"]])
            )
        else:
            # Retire only untouched fixture variants, never user additions/edits.
            connection.execute(sa.delete(practices).where(match))
    connection.execute(insert(practices).values(new_practices).on_conflict_do_nothing())
    for row in old_categories:
        if row["uid"] not in desired_categories:
            # Custom records may still reference a former category.
            connection.execute(
                sa.delete(categories).where(
                    unchanged(categories, row),
                    ~sa.exists(
                        sa.select(practices.c.uid).where(
                            practices.c.category_uid == categories.c.uid
                        )
                    ),
                )
            )


def upgrade():
    transition(op.get_bind(), "0031", "0032")


def downgrade():
    transition(op.get_bind(), "0032", "0031")
