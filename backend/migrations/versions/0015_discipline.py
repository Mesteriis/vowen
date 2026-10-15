"""Explicit discipline consent, encrypted immutable versions and transition history."""

from alembic import op

revision = "0015"
down_revision = "0014"


def upgrade():
    op.execute("""
    CREATE TABLE discipline_records(id uuid PRIMARY KEY,author_id uuid NOT NULL REFERENCES users,
      recipient_id uuid NOT NULL REFERENCES users,idempotency_key uuid NOT NULL,
      current_version_id uuid,revision integer NOT NULL CHECK(revision>0),
      status varchar(20) NOT NULL CHECK(status IN
      ('proposed','accepted','in_progress','completed','confirmed','disputed','declined','cancelled')),
      UNIQUE(author_id,idempotency_key),CHECK(author_id<>recipient_id));
    CREATE TABLE discipline_versions(id uuid PRIMARY KEY,record_id uuid NOT NULL
      REFERENCES discipline_records,rule_version_id uuid REFERENCES rule_versions,
      occurrence_id uuid REFERENCES ritual_occurrences,created_at timestamptz NOT NULL,
      key_id varchar(100) NOT NULL,nonce bytea NOT NULL,ciphertext bytea NOT NULL);
    ALTER TABLE discipline_records ADD CONSTRAINT current_discipline_version FOREIGN KEY
      (current_version_id) REFERENCES discipline_versions;
    CREATE TABLE discipline_reviewers(record_id uuid NOT NULL REFERENCES discipline_records,
      user_id uuid NOT NULL REFERENCES users,PRIMARY KEY(record_id,user_id));
    CREATE TABLE discipline_transitions(id uuid PRIMARY KEY,record_id uuid NOT NULL
      REFERENCES discipline_records,version_id uuid NOT NULL REFERENCES discipline_versions,
      revision integer NOT NULL,status varchar(20) NOT NULL,actor_id uuid NOT NULL REFERENCES users,
      created_at timestamptz NOT NULL,key_id varchar(100) NOT NULL,nonce bytea NOT NULL,
      ciphertext bytea NOT NULL,UNIQUE(record_id,revision));
    CREATE INDEX discipline_recipient ON discipline_records(recipient_id);
    """)


def downgrade():
    op.execute("""DROP TABLE discipline_transitions,discipline_reviewers;
    ALTER TABLE discipline_records DROP CONSTRAINT current_discipline_version;
    DROP TABLE discipline_versions,discipline_records;""")
