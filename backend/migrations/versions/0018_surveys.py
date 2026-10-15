"""Immutable survey plans, independently pausable audiences and unique waves."""

from alembic import op

revision = "0018"
down_revision = "0017"


def upgrade():
    op.execute("""
    CREATE TABLE survey_schedules(id uuid PRIMARY KEY,author_id uuid NOT NULL REFERENCES users,
      recipient_id uuid NOT NULL REFERENCES users,
      form_version_id uuid NOT NULL REFERENCES form_versions,
      idempotency_key uuid NOT NULL,config jsonb NOT NULL,
      ritual_assignment_id uuid REFERENCES ritual_assignments,source_revision integer,
      authority_revision integer,revision integer NOT NULL,owner_paused boolean NOT NULL,
      recipient_paused boolean NOT NULL,blocked_through timestamptz,created_at timestamptz NOT NULL,
      checked_at timestamptz,watermark date,UNIQUE(author_id,idempotency_key));
    CREATE TABLE survey_waves(id uuid PRIMARY KEY,
      schedule_id uuid NOT NULL REFERENCES survey_schedules,
      event_key varchar(100) NOT NULL,due_at timestamptz NOT NULL,
      occurrence_id uuid REFERENCES ritual_occurrences,
      invitation_id uuid REFERENCES form_invitations,
      status varchar(20) NOT NULL CHECK(status IN ('created','skipped')),reason varchar(40),
      UNIQUE(schedule_id,event_key));
    CREATE INDEX survey_wave_invitation ON survey_waves(invitation_id);
    """)


def downgrade():
    op.execute("DROP TABLE survey_waves,survey_schedules")
