"""Durable consent generations and cancellation of rejected in-flight sends."""

from alembic import op

revision = "0014"
down_revision = "0013"


def upgrade():
    op.execute("""
    ALTER TABLE bot_contacts ADD COLUMN delivery_generation integer NOT NULL DEFAULT 0;
    ALTER TABLE member_deliveries ADD COLUMN consent_generation integer NOT NULL DEFAULT 0;
    ALTER TABLE member_deliveries ADD COLUMN cancellation_requested boolean NOT NULL DEFAULT false;
    ALTER TABLE member_deliveries ADD COLUMN authority_versions jsonb NOT NULL DEFAULT '{}';
    """)


def downgrade():
    op.execute("""
    ALTER TABLE member_deliveries DROP COLUMN authority_versions,
      DROP COLUMN cancellation_requested,
      DROP COLUMN consent_generation;
    ALTER TABLE bot_contacts DROP COLUMN delivery_generation;
    """)
