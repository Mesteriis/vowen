"""Personal channels and DST-aware quiet hours; generation-fenced outboxes."""

from alembic import op

revision = "0017"
down_revision = "0016"


def upgrade():
    op.execute("""
    ALTER TABLE user_preferences ADD COLUMN notification_channels jsonb NOT NULL
      DEFAULT '["in_app","telegram"]',
      ADD COLUMN notification_revision integer NOT NULL DEFAULT 1,
      ADD COLUMN notification_generation integer NOT NULL DEFAULT 0,
      ADD COLUMN quiet_enabled boolean NOT NULL DEFAULT false,
      ADD COLUMN quiet_start integer NOT NULL DEFAULT 1320 CHECK(quiet_start BETWEEN 0 AND 1439),
      ADD COLUMN quiet_end integer NOT NULL DEFAULT 480 CHECK(quiet_end BETWEEN 0 AND 1439);
    ALTER TABLE member_deliveries ADD COLUMN notification_generation integer NOT NULL DEFAULT 0;
    ALTER TABLE notification_deliveries
      ADD COLUMN notification_generation integer NOT NULL DEFAULT 0,
      ADD COLUMN consent_generation integer NOT NULL DEFAULT 0,
      ADD COLUMN deferred_until timestamptz;
    """)


def downgrade():
    op.execute("""ALTER TABLE notification_deliveries DROP COLUMN notification_generation,
      DROP COLUMN consent_generation,DROP COLUMN deferred_until;
    ALTER TABLE member_deliveries DROP COLUMN notification_generation;
    ALTER TABLE user_preferences DROP COLUMN notification_channels,
      DROP COLUMN notification_revision,
      DROP COLUMN notification_generation,DROP COLUMN quiet_enabled,DROP COLUMN quiet_start,
      DROP COLUMN quiet_end;""")
