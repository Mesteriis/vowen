"""Separate reusable punishment templates from assignment snapshots."""

from alembic import op

revision = "0025"
down_revision = "0024"


def upgrade():
    op.execute("""
    CREATE TABLE punishment_templates (
      id uuid PRIMARY KEY, relation_id uuid NOT NULL REFERENCES authority_relations(id),
      revision integer NOT NULL DEFAULT 1, archived boolean NOT NULL DEFAULT false,
      key_id varchar(100) NOT NULL, nonce bytea NOT NULL, ciphertext bytea NOT NULL);
    CREATE INDEX punishment_template_relation ON punishment_templates(relation_id);
    """)


def downgrade():
    op.drop_table("punishment_templates")
