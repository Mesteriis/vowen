"""Versioned forms, encrypted answers and scoped guest capabilities."""

from alembic import op

revision = "0007"
down_revision = "0006"


def upgrade():
    op.execute("""
CREATE TABLE forms (
    id UUID NOT NULL, 
    author_id UUID NOT NULL, 
    revision INTEGER NOT NULL, 
    current_version_id UUID NOT NULL, 
    PRIMARY KEY (id), 
    FOREIGN KEY(author_id) REFERENCES users (id)
)
    """)
    op.execute("""
CREATE TABLE form_versions (
    id UUID NOT NULL, 
    form_id UUID NOT NULL, 
    status VARCHAR(20) NOT NULL, 
    schema_body JSONB NOT NULL, 
    PRIMARY KEY (id), 
    FOREIGN KEY(form_id) REFERENCES forms (id)
)
    """)
    op.execute("""
CREATE TABLE form_invitations (
    id UUID NOT NULL, 
    version_id UUID NOT NULL, 
    creator_id UUID NOT NULL, 
    recipient_user_id UUID, 
    token_hash BYTEA, 
    activated_at TIMESTAMP WITH TIME ZONE, 
    revoked_at TIMESTAMP WITH TIME ZONE, 
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    retention_until TIMESTAMP WITH TIME ZONE NOT NULL, 
    PRIMARY KEY (id), 
    FOREIGN KEY(version_id) REFERENCES form_versions (id), 
    FOREIGN KEY(creator_id) REFERENCES users (id), 
    FOREIGN KEY(recipient_user_id) REFERENCES users (id), 
    UNIQUE (token_hash)
)
    """)
    op.execute("""
CREATE TABLE form_invitation_readers (
    invitation_id UUID NOT NULL, 
    user_id UUID NOT NULL, 
    PRIMARY KEY (invitation_id, user_id), 
    FOREIGN KEY(invitation_id) REFERENCES form_invitations (id), 
    FOREIGN KEY(user_id) REFERENCES users (id)
)
    """)
    op.execute("""
CREATE TABLE form_submissions (
    id UUID NOT NULL, 
    invitation_id UUID NOT NULL, 
    status VARCHAR(20) NOT NULL, 
    idempotency_key UUID, 
    key_id VARCHAR(100), 
    nonce BYTEA, 
    ciphertext BYTEA, 
    PRIMARY KEY (id), 
    UNIQUE (invitation_id), 
    FOREIGN KEY(invitation_id) REFERENCES form_invitations (id)
)
    """)
    op.execute("""
CREATE TABLE submission_receipts (
    id UUID NOT NULL, 
    submission_id UUID NOT NULL, 
    token_hash BYTEA NOT NULL, 
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    revoked_at TIMESTAMP WITH TIME ZONE, 
    PRIMARY KEY (id), 
    FOREIGN KEY(submission_id) REFERENCES form_submissions (id), 
    UNIQUE (token_hash)
)
    """)
    op.execute("""
CREATE TABLE guest_sessions (
    id UUID NOT NULL, 
    invitation_id UUID NOT NULL, 
    receipt_id UUID, 
    token_hash BYTEA NOT NULL, 
    csrf_hash BYTEA NOT NULL, 
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    PRIMARY KEY (id), 
    FOREIGN KEY(invitation_id) REFERENCES form_invitations (id), 
    FOREIGN KEY(receipt_id) REFERENCES submission_receipts (id), 
    UNIQUE (token_hash)
)
    """)
    op.execute("""
CREATE TABLE bot_contacts (
    telegram_id BIGINT NOT NULL, 
    allowed BOOLEAN NOT NULL, 
    PRIMARY KEY (telegram_id)
)
    """)
    op.execute("""
CREATE TABLE notification_deliveries (
    id UUID NOT NULL, 
    invitation_id UUID NOT NULL, 
    telegram_id BIGINT NOT NULL, 
    status VARCHAR(32) NOT NULL, 
    kind VARCHAR(20) NOT NULL,
    attempts INTEGER NOT NULL, 
    lease_id UUID, 
    lease_until TIMESTAMP WITH TIME ZONE, 
    key_id VARCHAR(100), 
    nonce BYTEA, 
    ciphertext BYTEA, 
    PRIMARY KEY (id), 
    CONSTRAINT one_event_delivery UNIQUE (invitation_id, telegram_id, kind), 
    FOREIGN KEY(invitation_id) REFERENCES form_invitations (id)
)
    """)
    op.execute("""
ALTER TABLE forms ADD CONSTRAINT current_form_version
    FOREIGN KEY (current_version_id) REFERENCES form_versions(id) DEFERRABLE INITIALLY DEFERRED
    """)


def downgrade():
    op.execute("ALTER TABLE forms DROP CONSTRAINT current_form_version")
    op.drop_table("notification_deliveries")
    op.drop_table("bot_contacts")
    op.drop_table("guest_sessions")
    op.drop_table("submission_receipts")
    op.drop_table("form_submissions")
    op.drop_table("form_invitation_readers")
    op.drop_table("form_invitations")
    op.drop_table("form_versions")
    op.drop_table("forms")
