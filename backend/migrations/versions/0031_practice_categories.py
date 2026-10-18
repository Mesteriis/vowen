"""Normalize practice categories into a referenced catalogue."""

import json
from pathlib import Path
from uuid import UUID

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, insert

revision = "0031"
down_revision = "0030"


def rows(filename):
    result = json.loads(
        (Path(__file__).resolve().parents[1] / "fixtures" / filename).read_text("utf-8")
    )
    for row in result:
        row["uid"] = UUID(row["uid"])
        if row.get("category_uid"):
            row["category_uid"] = UUID(row["category_uid"])
    return result


def upgrade():
    categories = op.create_table(
        "reference_practice_categories",
        sa.Column("uid", sa.UUID(), primary_key=True),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("icon", sa.Text(), nullable=True),
        sa.Column("url", sa.Text(), nullable=True),
        sa.Column("extra", JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.CheckConstraint("length(btrim(name)) > 0"),
    )
    op.create_index(
        "reference_practice_categories_name_unique",
        categories.name,
        [sa.text("lower(name)")],
        unique=True,
    )
    op.bulk_insert(categories, rows("0031-practice-categories.json"))
    op.add_column("reference_practices", sa.Column("category_uid", sa.UUID(), nullable=True))
    op.create_foreign_key(
        "reference_practices_category_fk",
        "reference_practices",
        categories.name,
        ["category_uid"],
        ["uid"],
        ondelete="RESTRICT",
    )
    op.create_index("ix_reference_practices_category_uid", "reference_practices", ["category_uid"])
    practices = sa.table(
        "reference_practices",
        sa.column("uid", sa.UUID()),
        sa.column("category_uid", sa.UUID()),
        sa.column("name", sa.Text()),
        sa.column("description", sa.Text()),
        sa.column("icon", sa.Text()),
        sa.column("url", sa.Text()),
        sa.column("extra", JSONB()),
    )
    connection = op.get_bind()
    old = {row["uid"]: row for row in rows("0030-practices.json")}
    for row in rows("0031-practices.json"):
        uid = row["uid"]
        # Assign by stable identity; preserve all user-edited content.
        connection.execute(
            sa.update(practices)
            .where(practices.c.uid == uid)
            .values(category_uid=row["category_uid"])
        )
        match = sa.and_(
            *(practices.c[key].is_not_distinct_from(value) for key, value in old[uid].items())
        )
        connection.execute(
            sa.update(practices)
            .where(match)
            .values(description=row["description"], extra=row["extra"])
        )
    connection.execute(
        insert(practices).values(rows("0031-practices.json")).on_conflict_do_nothing()
    )


def downgrade():
    op.drop_index("ix_reference_practices_category_uid", table_name="reference_practices")
    op.drop_constraint("reference_practices_category_fk", "reference_practices", type_="foreignkey")
    op.drop_column("reference_practices", "category_uid")
    op.drop_table("reference_practice_categories")
