"""Android challenges, independent secrets and explicit bot consent."""

import sqlalchemy as sa
from alembic import op

revision = "0004"
down_revision = "0003"


def upgrade():
    op.create_table(
        "android_login_challenges",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("start_token_hash", sa.String(64), unique=True, nullable=False),
        sa.Column("poll_secret_hash", sa.String(64), unique=True, nullable=False),
        sa.Column("nonce_hash", sa.String(64), nullable=False),
        sa.Column("device_label", sa.String(100), nullable=False),
        sa.Column("display_code", sa.String(6), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id")),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade():
    op.drop_table("android_login_challenges")
