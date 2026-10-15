"""Transactional Telegram outbox for ritual and reward notices, without backfill."""

from alembic import op

revision = "0013"
down_revision = "0012"


def upgrade():
    op.execute("""
    CREATE TABLE member_deliveries (
      id uuid PRIMARY KEY, user_id uuid NOT NULL REFERENCES users,
      ritual_notice_id uuid UNIQUE REFERENCES ritual_notices,
      reward_notice_id uuid UNIQUE REFERENCES reward_notices,
      occurrence_revision integer, status varchar(32) NOT NULL,
      attempts integer NOT NULL CHECK(attempts BETWEEN 0 AND 3),
      lease_id uuid, lease_until timestamptz,
      created_at timestamptz NOT NULL, available_at timestamptz NOT NULL,
      CHECK((ritual_notice_id IS NULL) <> (reward_notice_id IS NULL)),
      CHECK(status IN ('pending','claimed','sending','delivered','suppressed',
                       'uncertain','manual_delivery_required')));
    CREATE INDEX member_delivery_ready ON member_deliveries(status,available_at);
    """)


def downgrade():
    op.drop_table("member_deliveries")
