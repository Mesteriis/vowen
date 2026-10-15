"""Private profile preferences; labels never confer authority."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "0006"
down_revision = "0005"


def upgrade():
    op.create_table(
        "user_preferences",
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id"), primary_key=True),
        sa.Column("language", sa.String(2), nullable=False),
        sa.Column("timezone", sa.String(64), nullable=False),
        sa.Column("profile_labels", JSONB, nullable=False),
        sa.Column("profile_version", sa.Integer(), nullable=False),
    )
    op.execute("INSERT INTO user_preferences SELECT id, 'en', 'UTC', '[]'::jsonb, 1 FROM users")


def downgrade():
    op.drop_table("user_preferences")
