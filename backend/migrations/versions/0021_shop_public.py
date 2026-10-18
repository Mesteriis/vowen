"""Explicit shared marketplace visibility; private listings remain private by default."""

from alembic import op

revision = "0021"
down_revision = "0020"


def upgrade():
    op.execute("ALTER TABLE shop_listings ADD COLUMN audience_all boolean NOT NULL DEFAULT false")


def downgrade():
    op.execute("ALTER TABLE shop_listings DROP COLUMN audience_all")
