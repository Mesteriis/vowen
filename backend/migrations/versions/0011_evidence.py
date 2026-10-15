"""Private execution evidence, immutable report binding."""

from alembic import op

revision = "0011"
down_revision = "0010"


def upgrade():
    op.execute("""
    ALTER TABLE ritual_assignments ADD COLUMN evidence_policy jsonb NOT NULL
      DEFAULT '{"required": false,"allowed_types": ["link","photo","video"]}';
    CREATE TABLE ritual_evidence (
      id uuid PRIMARY KEY, occurrence_id uuid NOT NULL REFERENCES ritual_occurrences,
      owner_id uuid NOT NULL REFERENCES users, report_id uuid REFERENCES ritual_reports,
      idempotency_key uuid NOT NULL, digest bytea NOT NULL,
      kind varchar(10) NOT NULL CHECK(kind IN ('photo','video')),
      media_type varchar(30) NOT NULL, size integer NOT NULL CHECK(size>0 AND size<=8388608),
      created_at timestamptz NOT NULL, expires_at timestamptz,
      key_id varchar(100) NOT NULL, nonce bytea NOT NULL, ciphertext bytea NOT NULL,
      UNIQUE(occurrence_id,idempotency_key));
    CREATE INDEX ritual_evidence_owner ON ritual_evidence(owner_id);
    CREATE INDEX ritual_evidence_report ON ritual_evidence(report_id);
    """)


def downgrade():
    op.execute(
        "DROP TABLE ritual_evidence; ALTER TABLE ritual_assignments DROP COLUMN evidence_policy"
    )
