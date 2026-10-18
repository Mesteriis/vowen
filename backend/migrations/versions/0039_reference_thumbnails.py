"""Add independent thumbnail paths to reference catalogues; retain icons."""

import sqlalchemy as sa
from alembic import op

revision = "0039"
down_revision = "0038"

TABLES = (
    "reference_biological_sex",
    "reference_genders",
    "reference_practices",
    "reference_practice_categories",
    "reference_participant_compositions",
    "reference_devices",
    "reference_body_parts",
    "reference_materials",
    "reference_role_scenarios",
    "reference_interaction_formats",
    "reference_venues",
    "reference_health_conditions",
    "reference_allergens",
    "reference_timezones",
    "reference_relationship_types",
)


def upgrade() -> None:
    for table in TABLES:
        op.add_column(table, sa.Column("thumbnail", sa.Text(), nullable=True))


def downgrade() -> None:
    for table in reversed(TABLES):
        op.drop_column(table, "thumbnail")
