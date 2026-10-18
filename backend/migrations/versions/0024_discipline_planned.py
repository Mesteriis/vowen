"""Plan punishment execution without a separate acceptance step."""
from alembic import op

revision = "0024"
down_revision = "0023"


def upgrade():
    op.execute("""
    ALTER TABLE discipline_records DROP CONSTRAINT discipline_records_status_check;
    ALTER TABLE discipline_records ADD CONSTRAINT discipline_records_status_check
      CHECK(status IN ('planned','proposed','accepted','in_progress','completed',
        'confirmed','disputed','declined','cancelled'));
    """)


def downgrade():
    # Do not rewrite historical execution states to pretend acceptance happened.
    op.execute("""
    DO $$ BEGIN
      IF EXISTS(SELECT 1 FROM discipline_records WHERE status='planned')
        OR EXISTS(SELECT 1 FROM discipline_transitions WHERE status='planned') THEN
        RAISE EXCEPTION 'Cannot downgrade while planned punishment history exists';
      END IF;
    END $$;
    ALTER TABLE discipline_records DROP CONSTRAINT discipline_records_status_check;
    ALTER TABLE discipline_records ADD CONSTRAINT discipline_records_status_check
      CHECK(status IN ('proposed','accepted','in_progress','completed','confirmed',
        'disputed','declined','cancelled'));
    """)
