"""Response retention starts on submission; draft lifetime follows invitation TTL."""

import sqlalchemy as sa
from alembic import op

revision = "0008"
down_revision = "0007"


def upgrade():
    op.add_column(
        "form_invitations",
        sa.Column("retention_days", sa.Integer(), nullable=False, server_default="90"),
    )
    op.alter_column("form_invitations", "retention_until", nullable=True)
    op.execute(
        "UPDATE form_invitations SET retention_until=NULL WHERE id IN "
        "(SELECT invitation_id FROM form_submissions WHERE status='draft')"
    )
    op.create_check_constraint(
        "response_retention_bounds", "form_invitations", "retention_days BETWEEN 1 AND 365"
    )


def downgrade():
    op.drop_constraint("response_retention_bounds", "form_invitations")
    op.execute(
        "UPDATE form_invitations SET retention_until=expires_at WHERE retention_until IS NULL"
    )
    op.alter_column("form_invitations", "retention_until", nullable=False)
    op.drop_column("form_invitations", "retention_days")
