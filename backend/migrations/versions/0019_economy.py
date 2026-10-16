"""Relationship wallets, immutable currency ledger, shop and ritual reward bundles."""

from alembic import op

revision = "0019"
down_revision = "0018"


def upgrade():
    op.execute("""
    ALTER TABLE ritual_reward_policies ALTER COLUMN reward_version_id DROP NOT NULL;
    ALTER TABLE ritual_reward_policies ADD COLUMN relation_id uuid REFERENCES authority_relations;
    ALTER TABLE ritual_reward_policies ADD COLUMN currency_amount integer NOT NULL DEFAULT 0
      CHECK(currency_amount>=0);
    ALTER TABLE ritual_reward_policies ADD COLUMN automatic_accept boolean NOT NULL DEFAULT false;
    UPDATE ritual_reward_policies p SET relation_id=r.id
      FROM ritual_assignments a,authority_relations r
      WHERE a.id=p.assignment_id AND r.dominant_user_id=p.issuer_id
        AND r.submissive_user_id=a.recipient_id AND r.status<>'revoked';
    CREATE TABLE ritual_reward_items(id uuid PRIMARY KEY,policy_id uuid NOT NULL REFERENCES
      ritual_reward_policies,
      reward_version_id uuid NOT NULL REFERENCES
      reward_definition_versions,UNIQUE(policy_id,reward_version_id));
    INSERT INTO ritual_reward_items SELECT id,id,reward_version_id FROM ritual_reward_policies;
    ALTER TABLE reward_grants ADD COLUMN policy_item_id uuid REFERENCES ritual_reward_items;
    UPDATE reward_grants SET policy_item_id=reward_policy_id WHERE reward_policy_id IS NOT NULL;
    ALTER TABLE reward_grants DROP CONSTRAINT
      reward_grants_occurrence_id_reward_policy_id_recipient_id_key;
    ALTER TABLE reward_grants ADD CONSTRAINT one_reward_per_policy_item
      UNIQUE(occurrence_id,policy_item_id,recipient_id);
    CREATE TABLE relation_wallets(relation_id uuid PRIMARY KEY REFERENCES authority_relations);
    CREATE TABLE shop_listings(id uuid PRIMARY KEY,relation_id uuid NOT NULL REFERENCES
      authority_relations,
      reward_version_id uuid NOT NULL REFERENCES reward_definition_versions,price integer NOT
      NULL CHECK(price>0),
      active boolean NOT NULL DEFAULT true,revision integer NOT NULL DEFAULT 1);
    CREATE TABLE currency_entries(id uuid PRIMARY KEY,relation_id uuid NOT NULL REFERENCES
      relation_wallets,
      actor_id uuid NOT NULL REFERENCES users,amount bigint NOT NULL CHECK(amount<>0),
      kind varchar(20) NOT NULL CHECK(kind IN ('manual','ritual','purchase')),idempotency_key uuid,
      occurrence_id uuid REFERENCES ritual_occurrences,policy_id uuid REFERENCES
      ritual_reward_policies,
      grant_id uuid REFERENCES reward_grants,listing_id uuid REFERENCES shop_listings,
      key_id varchar(100) NOT NULL,nonce bytea NOT NULL,ciphertext bytea NOT NULL,
      created_at timestamptz NOT NULL,
      UNIQUE(relation_id,actor_id,idempotency_key),UNIQUE(relation_id,occurrence_id,policy_id),
      CHECK((kind='manual' AND amount>0 AND idempotency_key IS NOT NULL AND occurrence_id IS
      NULL AND policy_id IS NULL AND grant_id IS NULL AND listing_id IS NULL)
       OR (kind='ritual' AND amount>0 AND idempotency_key IS NULL AND occurrence_id IS NOT NULL
      AND policy_id IS NOT NULL AND grant_id IS NULL AND listing_id IS NULL)
       OR (kind='purchase' AND amount<0 AND idempotency_key IS NOT NULL AND occurrence_id IS
      NULL AND policy_id IS NULL AND grant_id IS NOT NULL AND listing_id IS NOT NULL)));
    CREATE INDEX currency_entries_history ON currency_entries(relation_id,created_at,id);
    CREATE FUNCTION currency_entries_immutable() RETURNS trigger LANGUAGE plpgsql AS $$
    BEGIN RAISE EXCEPTION 'Currency entries are append-only'; END; $$;
    CREATE TRIGGER currency_entries_immutable BEFORE UPDATE OR DELETE ON currency_entries
      FOR EACH ROW EXECUTE FUNCTION currency_entries_immutable();
    """)


def downgrade():
    # Legacy-only databases can roll back. Never silently discard earned currency
    # or a bundle/shop created after this migration.
    op.execute("""
    DO $$ BEGIN
      IF EXISTS(SELECT 1 FROM currency_entries) OR EXISTS(SELECT 1 FROM shop_listings)
       OR EXISTS(SELECT 1 FROM ritual_reward_policies WHERE automatic_accept OR currency_amount>0)
      THEN RAISE EXCEPTION 'Export economy data before downgrading'; END IF;
    END $$;
    DROP TABLE currency_entries,shop_listings,relation_wallets;
    DROP FUNCTION currency_entries_immutable();
    ALTER TABLE reward_grants DROP CONSTRAINT one_reward_per_policy_item;
    ALTER TABLE reward_grants DROP COLUMN policy_item_id;
    ALTER TABLE reward_grants ADD UNIQUE(occurrence_id,reward_policy_id,recipient_id);
    DROP TABLE ritual_reward_items;
    ALTER TABLE ritual_reward_policies DROP COLUMN automatic_accept;
    ALTER TABLE ritual_reward_policies DROP COLUMN currency_amount;
    ALTER TABLE ritual_reward_policies DROP COLUMN relation_id;
    ALTER TABLE ritual_reward_policies ALTER COLUMN reward_version_id SET NOT NULL;
    """)
