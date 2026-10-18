"""Add participant composition catalogue and group practice fixtures."""

import json
from pathlib import Path
from uuid import UUID

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, insert

revision = "0033"
down_revision = "0032"


def reference_table(name, practice=False):
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


compositions = reference_table("reference_participant_compositions")
categories = reference_table("reference_practice_categories")
practices = reference_table("reference_practices", True)


def rows(kind):
    result = json.loads(
        (Path(__file__).resolve().parents[1] / "fixtures" / f"0033-{kind}.json").read_text("utf-8")
    )
    for row in result:
        row["uid"] = UUID(row["uid"])
        if row.get("category_uid"):
            row["category_uid"] = UUID(row["category_uid"])
    return result


def seed(connection):
    for target, kind in (
        (compositions, "participant-compositions"),
        (categories, "practice-categories"),
        (practices, "practices"),
    ):
        connection.execute(insert(target).values(rows(kind)).on_conflict_do_nothing())


def upgrade():
    op.create_table(
        compositions.name,
        sa.Column("uid", sa.UUID(), primary_key=True),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("icon", sa.Text(), nullable=True),
        sa.Column("url", sa.Text(), nullable=True),
        sa.Column("extra", JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.CheckConstraint("length(btrim(name)) > 0"),
    )
    op.create_index(
        "reference_participant_compositions_name_unique",
        compositions.name,
        [sa.text("lower(name)")],
        unique=True,
    )
    seed(op.get_bind())


def downgrade():
    connection = op.get_bind()
    for row in rows("practices"):
        connection.execute(
            sa.delete(practices).where(
                sa.and_(
                    *(practices.c[key].is_not_distinct_from(value) for key, value in row.items())
                )
            )
        )
    for row in rows("practice-categories"):
        connection.execute(
            sa.delete(categories).where(
                sa.and_(
                    *(categories.c[key].is_not_distinct_from(value) for key, value in row.items())
                ),
                ~sa.exists(
                    sa.select(practices.c.uid).where(practices.c.category_uid == categories.c.uid)
                ),
            )
        )
    op.drop_table(compositions.name)
