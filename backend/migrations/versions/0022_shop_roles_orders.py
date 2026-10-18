"""Explicit shop roles, catalogue controls and reserved purchase approvals."""

from alembic import op

revision = "0022"
down_revision = "0021"


def upgrade():
    op.execute("""
    ALTER TABLE users ADD COLUMN shop_role varchar(20) NOT NULL DEFAULT 'viewer'
      CHECK(shop_role IN ('viewer','dominant','switch','bottom'));
    WITH roles AS (
      SELECT u.id,
        EXISTS(SELECT 1 FROM authority_relations r WHERE r.dominant_user_id=u.id
          AND r.status='active' AND (SELECT count(*) FROM agreement_consents c
            WHERE c.relation_version_id=r.relation_version_id)=2) AS upper_role,
        EXISTS(SELECT 1 FROM authority_relations r WHERE r.submissive_user_id=u.id
          AND r.status='active' AND (SELECT count(*) FROM agreement_consents c
            WHERE c.relation_version_id=r.relation_version_id)=2) AS lower_role
      FROM users u
    ) UPDATE users u SET shop_role=CASE
      WHEN roles.upper_role AND roles.lower_role THEN 'switch'
      WHEN roles.upper_role THEN 'dominant'
      WHEN roles.lower_role THEN 'bottom' ELSE 'viewer' END
      FROM roles WHERE u.id=roles.id;
    ALTER TABLE reward_definitions ADD COLUMN shop_enabled boolean NOT NULL DEFAULT true;
    ALTER TABLE reward_definitions ADD COLUMN shop_deleted boolean NOT NULL DEFAULT false;
    ALTER TABLE shop_listings ALTER COLUMN relation_id DROP NOT NULL;
    CREATE TABLE shop_relation_preferences(
      relation_id uuid NOT NULL REFERENCES authority_relations,
      definition_id uuid NOT NULL REFERENCES reward_definitions,
      enabled boolean NOT NULL DEFAULT true,
      revision integer NOT NULL DEFAULT 1,
      PRIMARY KEY(relation_id,definition_id));
    CREATE TABLE purchase_orders(
      grant_id uuid PRIMARY KEY REFERENCES reward_grants,
      relation_id uuid NOT NULL REFERENCES authority_relations,
      listing_id uuid NOT NULL REFERENCES shop_listings,
      buyer_id uuid NOT NULL REFERENCES users,
      amount integer NOT NULL CHECK(amount>0),
      idempotency_key uuid NOT NULL,
      UNIQUE(relation_id,buyer_id,idempotency_key));
    CREATE INDEX purchase_orders_wallet ON purchase_orders(relation_id);
    ALTER TABLE reward_grants DROP CONSTRAINT reward_grants_status_check;
    ALTER TABLE reward_grants ADD CONSTRAINT reward_grants_status_check
      CHECK(status IN ('offered','accepted','declined','delivered','cancelled',
                       'pending_approval','redeemed'));
    """)


def downgrade():
    op.execute("""
    DO $$ BEGIN
      IF EXISTS(SELECT 1 FROM purchase_orders) OR EXISTS(
        SELECT 1 FROM reward_grants WHERE status IN ('pending_approval','redeemed'))
        OR EXISTS(SELECT 1 FROM shop_listings WHERE relation_id IS NULL)
      THEN RAISE EXCEPTION 'Cannot discard shop purchase history or global products'; END IF;
    END $$;
    DROP TABLE purchase_orders,shop_relation_preferences;
    ALTER TABLE shop_listings ALTER COLUMN relation_id SET NOT NULL;
    ALTER TABLE reward_definitions DROP COLUMN shop_enabled,DROP COLUMN shop_deleted;
    ALTER TABLE reward_grants DROP CONSTRAINT reward_grants_status_check;
    ALTER TABLE reward_grants ADD CONSTRAINT reward_grants_status_check
      CHECK(status IN ('offered','accepted','declined','delivered','cancelled'));
    ALTER TABLE users DROP COLUMN shop_role;
    """)
