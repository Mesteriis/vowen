"""Encrypted private diary with author-controlled snapshot readership."""

from alembic import op

revision = "0016"
down_revision = "0015"


def upgrade():
    op.execute("""
    CREATE TABLE journal_entries(id uuid PRIMARY KEY,author_id uuid NOT NULL REFERENCES users,
      revision integer NOT NULL CHECK(revision>0),visibility varchar(24) NOT NULL
      CHECK(visibility IN ('private','selected','all_current_members')),
      published boolean NOT NULL,created_at timestamptz NOT NULL,updated_at timestamptz NOT NULL,
      key_id varchar(100) NOT NULL,nonce bytea NOT NULL,ciphertext bytea NOT NULL);
    CREATE TABLE journal_readers(entry_id uuid NOT NULL
      REFERENCES journal_entries ON DELETE CASCADE,
      user_id uuid NOT NULL REFERENCES users,PRIMARY KEY(entry_id,user_id));
    CREATE INDEX journal_author ON journal_entries(author_id);
    CREATE INDEX journal_reader ON journal_readers(user_id);
    """)


def downgrade():
    op.execute("DROP TABLE journal_readers,journal_entries")
