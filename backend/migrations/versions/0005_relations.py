"""Contextual authority, immutable encrypted agreements and exact-version consent."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "0005"
down_revision = "0004"


def upgrade():
    op.create_table(
        "authority_relations",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("dominant_user_id", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("submissive_user_id", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("relation_version_id", sa.Uuid()),
        sa.CheckConstraint("dominant_user_id <> submissive_user_id", name="no_self_relation"),
    )
    op.create_index(
        "one_current_directed_pair",
        "authority_relations",
        ["dominant_user_id", "submissive_user_id"],
        unique=True,
        postgresql_where=sa.text("status <> 'revoked'"),
    )
    op.create_table(
        "relation_versions",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "relation_id", sa.Uuid(), sa.ForeignKey("authority_relations.id"), nullable=False
        ),
        sa.Column("scopes", JSONB, nullable=False),
        sa.Column("key_id", sa.String(100), nullable=False),
        sa.Column("nonce", sa.LargeBinary(), nullable=False),
        sa.Column("ciphertext", sa.LargeBinary(), nullable=False),
    )
    op.create_foreign_key(
        "current_relation_version",
        "authority_relations",
        "relation_versions",
        ["relation_version_id"],
        ["id"],
    )
    op.create_table(
        "agreement_consents",
        sa.Column(
            "relation_version_id",
            sa.Uuid(),
            sa.ForeignKey("relation_versions.id"),
            primary_key=True,
        ),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id"), primary_key=True),
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade():
    op.drop_table("agreement_consents")
    op.drop_constraint("current_relation_version", "authority_relations", type_="foreignkey")
    op.drop_table("relation_versions")
    op.drop_table("authority_relations")
