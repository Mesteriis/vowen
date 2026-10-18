"""Populate only empty reference thumbnails from the immutable generated fixture snapshot."""

import json
from pathlib import Path
from uuid import UUID

import sqlalchemy as sa
from alembic import op

revision = "0040"
down_revision = "0039"
TABLES = {
    "biological-sex": "reference_biological_sex",
    "genders": "reference_genders",
    "practices": "reference_practices",
    "practice-categories": "reference_practice_categories",
    "participant-compositions": "reference_participant_compositions",
    "devices": "reference_devices",
    "body-parts": "reference_body_parts",
    "materials": "reference_materials",
    "role-scenarios": "reference_role_scenarios",
    "interaction-formats": "reference_interaction_formats",
    "venues": "reference_venues",
    "health-conditions": "reference_health_conditions",
    "allergens": "reference_allergens",
    "timezones": "reference_timezones",
    "relationship-types": "reference_relationship_types",
}


def apply(connection: sa.Connection, reverse: bool = False) -> None:
    rows = json.loads(
        (
            Path(__file__).resolve().parents[1] / "fixtures" / "0040-reference-thumbnails.json"
        ).read_text("utf-8")
    )
    for row in rows:
        target = sa.table(
            TABLES[row["kind"]],
            sa.column("uid", sa.UUID()),
            sa.column("thumbnail", sa.Text()),
        )
        condition = (
            target.c.thumbnail == row["thumbnail"] if reverse else target.c.thumbnail.is_(None)
        )
        connection.execute(
            sa.update(target)
            .where(target.c.uid == UUID(row["uid"]), condition)
            .values(thumbnail=None if reverse else row["thumbnail"])
        )


def upgrade() -> None:
    apply(op.get_bind())


def downgrade() -> None:
    apply(op.get_bind(), reverse=True)
