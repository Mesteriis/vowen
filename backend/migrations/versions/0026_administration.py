"""Independent space administrators and serialized role changes."""

from alembic import op

revision = "0026"
down_revision = "0025"


def upgrade():
    op.execute("""
    ALTER TABLE users ADD COLUMN is_admin boolean NOT NULL DEFAULT false;
    CREATE TABLE administration_state (
      id integer PRIMARY KEY CHECK (id=1), revision integer NOT NULL DEFAULT 1);
    INSERT INTO administration_state (id,revision) VALUES (1,1);
    UPDATE users SET is_admin=true WHERE id=(
      SELECT id FROM users ORDER BY created_at,id LIMIT 1);
    CREATE TABLE administrator_events (
      id uuid PRIMARY KEY, actor_id uuid NOT NULL REFERENCES users(id),
      target_id uuid NOT NULL REFERENCES users(id), action varchar(16) NOT NULL,
      created_at timestamptz NOT NULL);
    """)


def downgrade():
    op.drop_table("administrator_events")
    op.drop_table("administration_state")
    op.drop_column("users", "is_admin")
