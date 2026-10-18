"""Bind private profile readers to the explicitly shared relationship incarnation."""

import sqlalchemy as sa
from alembic import op

revision = "0045"
down_revision = "0044"


def upgrade():
    # Existing grants remain closed until explicitly shared again; never infer authority.
    op.add_column("participant_profile_readers", sa.Column("relation_id", sa.UUID(), nullable=True))
    op.create_foreign_key(
        "profile_reader_relation",
        "participant_profile_readers",
        "authority_relations",
        ["relation_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.add_column(
        "participant_profile_drafts",
        sa.Column("visibility_edited", sa.Boolean(), nullable=False, server_default=sa.false()),
    )


def downgrade():
    op.drop_column("participant_profile_drafts", "visibility_edited")
    op.drop_constraint("profile_reader_relation", "participant_profile_readers", type_="foreignkey")
    op.drop_column("participant_profile_readers", "relation_id")
