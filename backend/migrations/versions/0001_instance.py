"""Singleton instance settings."""
from alembic import op
import sqlalchemy as sa

revision = '0001'
down_revision = None


def upgrade():
    op.create_table('instance_settings',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('display_name', sa.String(100), nullable=False),
        sa.CheckConstraint('id = 1', name='singleton_instance'))
    op.execute("INSERT INTO instance_settings (id, display_name) VALUES (1, 'Vowen')")


def downgrade():
    op.drop_table('instance_settings')
