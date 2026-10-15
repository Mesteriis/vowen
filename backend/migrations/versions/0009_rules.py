"""Encrypted rule versions and independent exact-version assignments."""

import sqlalchemy as sa
from alembic import op

revision = "0009"
down_revision = "0008"


def upgrade():
    op.create_table(
        "rules",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column("author_id", sa.UUID(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("current_version_id", sa.UUID()),
    )
    op.create_table(
        "rule_versions",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column("rule_id", sa.UUID(), sa.ForeignKey("rules.id"), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("key_id", sa.String(100), nullable=False),
        sa.Column("nonce", sa.LargeBinary(), nullable=False),
        sa.Column("ciphertext", sa.LargeBinary(), nullable=False),
        sa.CheckConstraint("status IN ('draft','published','archived')"),
    )
    op.create_foreign_key(
        "current_rule_version", "rules", "rule_versions", ["current_version_id"], ["id"]
    )
    op.create_table(
        "rule_assignments",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column("rule_id", sa.UUID(), sa.ForeignKey("rules.id"), nullable=False),
        sa.Column("rule_version_id", sa.UUID(), sa.ForeignKey("rule_versions.id"), nullable=False),
        sa.Column("recipient_id", sa.UUID(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("issuer_id", sa.UUID(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(24), nullable=False),
        sa.Column("accepted_at", sa.DateTime(timezone=True)),
        sa.Column("decided_at", sa.DateTime(timezone=True)),
        sa.UniqueConstraint("rule_version_id", "recipient_id", name="one_rule_version_recipient"),
        sa.CheckConstraint("status IN ('pending_acceptance','active','paused','revoked')"),
    )
    op.create_index(
        "one_active_rule_recipient",
        "rule_assignments",
        ["rule_id", "recipient_id"],
        unique=True,
        postgresql_where=sa.text("status='active'"),
    )
    op.create_table(
        "rule_assignment_managers",
        sa.Column(
            "assignment_id", sa.UUID(), sa.ForeignKey("rule_assignments.id"), primary_key=True
        ),
        sa.Column("user_id", sa.UUID(), sa.ForeignKey("users.id"), primary_key=True),
    )


def downgrade():
    op.drop_table("rule_assignment_managers")
    op.drop_table("rule_assignments")
    op.drop_constraint("current_rule_version", "rules", type_="foreignkey")
    op.drop_table("rule_versions")
    op.drop_table("rules")
