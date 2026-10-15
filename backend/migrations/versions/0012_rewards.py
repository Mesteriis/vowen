"""Versioned rewards, explicit policy, unique grants and immutable transition history."""

from alembic import op

revision = "0012"
down_revision = "0011"


def upgrade():
    op.execute("""
    CREATE TABLE reward_definitions(id uuid PRIMARY KEY,author_id uuid NOT NULL REFERENCES users,
      revision integer NOT NULL,current_version_id uuid);
    CREATE TABLE reward_definition_versions(id uuid PRIMARY KEY,definition_id uuid NOT NULL
      REFERENCES reward_definitions,
      key_id varchar(100) NOT NULL,nonce bytea NOT NULL,ciphertext bytea NOT NULL);
    ALTER TABLE reward_definitions ADD CONSTRAINT current_reward_version FOREIGN
      KEY(current_version_id) REFERENCES reward_definition_versions;
    CREATE TABLE ritual_reward_policies(id uuid PRIMARY KEY,assignment_id uuid NOT NULL
      REFERENCES ritual_assignments,
      reward_version_id uuid NOT NULL REFERENCES reward_definition_versions,issuer_id uuid NOT
      NULL REFERENCES users,created_at timestamptz NOT NULL);
    ALTER TABLE ritual_assignments ADD COLUMN reward_policy_id uuid REFERENCES
      ritual_reward_policies;
    ALTER TABLE ritual_occurrences ADD COLUMN reward_policy_id uuid REFERENCES
      ritual_reward_policies;
    CREATE TABLE reward_grants(id uuid PRIMARY KEY,reward_version_id uuid NOT NULL REFERENCES
      reward_definition_versions,
      recipient_id uuid NOT NULL REFERENCES users,issuer_id uuid NOT NULL REFERENCES users,
      occurrence_id uuid REFERENCES ritual_occurrences,reward_policy_id uuid REFERENCES
      ritual_reward_policies,
      idempotency_key uuid,revision integer NOT NULL,status varchar(20) NOT NULL CHECK(status IN
      ('offered','accepted','declined','delivered','cancelled')),
      created_at timestamptz NOT
      NULL,UNIQUE(issuer_id,idempotency_key),UNIQUE(occurrence_id,reward_policy_id,recipient_id),
      CHECK((occurrence_id IS NULL AND reward_policy_id IS NULL AND idempotency_key IS NOT NULL)
      OR (occurrence_id IS NOT NULL AND reward_policy_id IS NOT NULL AND idempotency_key IS
      NULL)));
    CREATE TABLE reward_transitions(id uuid PRIMARY KEY,grant_id uuid NOT NULL REFERENCES
      reward_grants,
      revision integer NOT NULL,status varchar(20) NOT NULL,actor_id uuid NOT NULL REFERENCES users,
      created_at timestamptz NOT NULL,UNIQUE(grant_id,revision));
    CREATE TABLE reward_notices(id uuid PRIMARY KEY,grant_id uuid NOT NULL REFERENCES
      reward_grants,user_id uuid NOT NULL REFERENCES users,
      revision integer NOT NULL,created_at timestamptz NOT NULL,UNIQUE(grant_id,user_id,revision));
    """)


def downgrade():
    op.execute("""DROP TABLE reward_notices, reward_transitions,reward_grants;
    ALTER TABLE ritual_occurrences DROP COLUMN reward_policy_id;
    ALTER TABLE ritual_assignments DROP COLUMN reward_policy_id;
    DROP TABLE ritual_reward_policies;
    ALTER TABLE reward_definitions DROP CONSTRAINT current_reward_version;
    DROP TABLE reward_definition_versions,reward_definitions""")
