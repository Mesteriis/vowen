"""Relationship-scoped encrypted punishment dictionaries."""

from alembic import op

revision = "0023"
down_revision = "0022"


def upgrade():
    op.execute("""
    CREATE TABLE discipline_dictionary (
      id uuid PRIMARY KEY,
      relation_id uuid NOT NULL REFERENCES authority_relations(id),
      kind varchar(20) NOT NULL CHECK(kind IN ('device','body_part')),
      name_digest varchar(64) NOT NULL,
      key_id varchar(100) NOT NULL,
      nonce bytea NOT NULL,
      ciphertext bytea NOT NULL,
      UNIQUE(relation_id,kind,name_digest)
    )
    """)


def downgrade():
    op.drop_table("discipline_dictionary")
