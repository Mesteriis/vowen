"""Private participant profiles, drafts and typed reference selections."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "0044"
down_revision = "0043"

TARGETS = {
    "sex_preference": "reference_biological_sex",
    "gender_preference": "reference_genders",
    "relationship_type_uids": "reference_relationship_types",
    "composition_uids": "reference_participant_compositions",
    "interaction_format_uids": "reference_interaction_formats",
    "devices": "reference_devices",
    "body_parts": "reference_body_parts",
    "materials": "reference_materials",
    "role_scenarios": "reference_role_scenarios",
    "venues": "reference_venues",
    "condition_uids": "reference_health_conditions",
    "allergen_uids": "reference_allergens",
    "care_practice_uids": "reference_practices",
    "biological_sex_uid": "reference_biological_sex",
    "gender_uid": "reference_genders",
}


def upgrade():
    op.create_table(
        "participant_profiles",
        sa.Column(
            "user_id", sa.UUID(), sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
        ),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("content", JSONB(), nullable=False),
        sa.Column("step", sa.Integer(), nullable=False),
        sa.Column("deferred", sa.Boolean(), nullable=False),
        sa.Column("completed", sa.Boolean(), nullable=False),
        sa.Column("draft_sequence", sa.Integer(), nullable=False),
    )
    op.create_table(
        "participant_profile_drafts",
        sa.Column(
            "user_id",
            sa.UUID(),
            sa.ForeignKey("participant_profiles.user_id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("document", JSONB(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("base_profile_version", sa.Integer(), nullable=False),
        sa.Column("base_account_version", sa.Integer(), nullable=False),
        sa.Column("step", sa.Integer(), nullable=False),
        sa.Column("deferred", sa.Boolean(), nullable=False),
    )
    op.create_table(
        "participant_profile_readers",
        sa.Column(
            "owner_id",
            sa.UUID(),
            sa.ForeignKey("participant_profiles.user_id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("section", sa.String(20), primary_key=True),
        sa.Column(
            "reader_id", sa.UUID(), sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
        ),
    )
    op.create_table(
        "participant_practice_preferences",
        sa.Column(
            "owner_id",
            sa.UUID(),
            sa.ForeignKey("participant_profiles.user_id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "practice_uid",
            sa.UUID(),
            sa.ForeignKey("reference_practices.uid", ondelete="RESTRICT"),
            primary_key=True,
        ),
        sa.Column("attitude", sa.String(20), nullable=False),
        sa.Column("experience", sa.String(20), nullable=False),
        sa.Column("participation", sa.String(20), nullable=False),
        sa.Column("conditions", sa.String(2000), nullable=False),
    )
    for key, target in TARGETS.items():
        op.create_table(
            "participant_profile_" + key,
            sa.Column(
                "owner_id",
                sa.UUID(),
                sa.ForeignKey("participant_profiles.user_id", ondelete="CASCADE"),
                primary_key=True,
            ),
            sa.Column(
                "uid",
                sa.UUID(),
                sa.ForeignKey(target + ".uid", ondelete="RESTRICT"),
                primary_key=True,
            ),
            sa.Column("attributes", JSONB(), nullable=False),
        )


def downgrade():
    for key in reversed(TARGETS):
        op.drop_table("participant_profile_" + key)
    for name in (
        "participant_practice_preferences",
        "participant_profile_readers",
        "participant_profile_drafts",
        "participant_profiles",
    ):
        op.drop_table(name)
