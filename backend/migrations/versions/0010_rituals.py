"""Ritual versions, schedules, independent slots, encrypted report attempts and notices."""

from alembic import op

revision = "0010"
down_revision = "0009"


def upgrade():
    op.execute("""
    CREATE TABLE rituals (id uuid PRIMARY KEY, author_id uuid NOT NULL REFERENCES users,
      revision integer NOT NULL, current_version_id uuid);
    CREATE TABLE ritual_versions (id uuid PRIMARY KEY, ritual_id uuid NOT NULL REFERENCES rituals,
      status varchar(20) NOT NULL CHECK(status IN ('draft','published','archived')),
      key_id varchar(100) NOT NULL, nonce bytea NOT NULL, ciphertext bytea NOT NULL);
    ALTER TABLE rituals ADD CONSTRAINT current_ritual_version FOREIGN KEY(current_version_id)
REFERENCES ritual_versions;
    CREATE TABLE ritual_assignments (id uuid PRIMARY KEY, ritual_version_id uuid NOT NULL
REFERENCES ritual_versions,
      recipient_id uuid NOT NULL REFERENCES users, issuer_id uuid NOT NULL REFERENCES users,
      approval_required boolean NOT NULL, status varchar(20) NOT NULL CHECK(status IN
('active','paused','revoked')),
      revision integer NOT NULL, current_schedule_id uuid, watermark date NOT NULL,
      idempotency_key uuid NOT NULL, request_hash bytea NOT NULL,
      CONSTRAINT one_ritual_assignment_request UNIQUE(issuer_id,idempotency_key));
    CREATE TABLE ritual_schedules (id uuid PRIMARY KEY, assignment_id uuid NOT NULL REFERENCES
ritual_assignments,
      starts_on date NOT NULL, ends_on date, spec jsonb NOT NULL);
    ALTER TABLE ritual_assignments ADD CONSTRAINT current_ritual_schedule FOREIGN
KEY(current_schedule_id) REFERENCES ritual_schedules;
    CREATE TABLE ritual_reviewers (assignment_id uuid NOT NULL REFERENCES ritual_assignments,
      user_id uuid NOT NULL REFERENCES users, PRIMARY KEY(assignment_id,user_id));
    CREATE TABLE ritual_occurrences (id uuid PRIMARY KEY, assignment_id uuid NOT NULL REFERENCES
ritual_assignments,
      schedule_id uuid NOT NULL REFERENCES ritual_schedules, local_day date NOT NULL,
      due_at timestamptz NOT NULL, expires_at timestamptz NOT NULL, revision integer NOT NULL,
      status varchar(20) NOT NULL CHECK(status IN
('scheduled','submitted','approved','needs_changes','missed','skipped','cancelled')),
      CONSTRAINT one_ritual_local_slot UNIQUE(assignment_id,local_day));
    CREATE TABLE ritual_reports (id uuid PRIMARY KEY, attempt integer NOT NULL, occurrence_id
uuid NOT NULL REFERENCES ritual_occurrences,
      idempotency_key uuid NOT NULL, submitted_at timestamptz NOT NULL, decision varchar(20),
      reviewer_id uuid REFERENCES users, reviewed_at timestamptz, key_id varchar(100) NOT NULL,
      nonce bytea NOT NULL, ciphertext bytea NOT NULL,
      CONSTRAINT one_ritual_report_request UNIQUE(occurrence_id,idempotency_key),
UNIQUE(occurrence_id,attempt));
    CREATE TABLE ritual_notices (id uuid PRIMARY KEY, assignment_id uuid NOT NULL REFERENCES
ritual_assignments,
      occurrence_id uuid REFERENCES ritual_occurrences, user_id uuid NOT NULL REFERENCES users,
      event_key varchar(150) NOT NULL, kind varchar(30) NOT NULL, created_at timestamptz NOT NULL,
      CONSTRAINT one_ritual_notice UNIQUE(event_key,user_id));
    CREATE INDEX ritual_recipient ON ritual_assignments(recipient_id);
    CREATE INDEX ritual_pending_due ON ritual_occurrences(due_at) WHERE status='scheduled';
    """)


def downgrade():
    op.execute("""DROP TABLE ritual_notices, ritual_reports, ritual_occurrences, ritual_reviewers;
    ALTER TABLE ritual_assignments DROP CONSTRAINT current_ritual_schedule;
    DROP TABLE ritual_schedules, ritual_assignments;
    ALTER TABLE rituals DROP CONSTRAINT current_ritual_version;
    DROP TABLE ritual_versions, rituals;""")
