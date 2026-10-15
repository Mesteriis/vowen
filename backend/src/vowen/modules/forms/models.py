from datetime import datetime
from uuid import UUID, uuid4

from pydantic import JsonValue
from sqlalchemy import BigInteger, DateTime, ForeignKey, LargeBinary, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from vowen.core.database import Base


class Form(Base):
    __tablename__ = "forms"
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    author_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"))
    revision: Mapped[int] = mapped_column(default=1)
    current_version_id: Mapped[UUID] = mapped_column()


class FormVersion(Base):
    __tablename__ = "form_versions"
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    form_id: Mapped[UUID] = mapped_column(ForeignKey("forms.id"))
    status: Mapped[str] = mapped_column(String(20), default="draft")
    schema_body: Mapped[dict[str, JsonValue]] = mapped_column(JSONB)


class Invitation(Base):
    __tablename__ = "form_invitations"
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    version_id: Mapped[UUID] = mapped_column(ForeignKey("form_versions.id"))
    creator_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"))
    recipient_user_id: Mapped[UUID | None] = mapped_column(ForeignKey("users.id"))
    token_hash: Mapped[bytes | None] = mapped_column(LargeBinary, unique=True)
    activated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    retention_until: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class InvitationReader(Base):
    __tablename__ = "form_invitation_readers"
    invitation_id: Mapped[UUID] = mapped_column(ForeignKey("form_invitations.id"), primary_key=True)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), primary_key=True)


class Submission(Base):
    __tablename__ = "form_submissions"
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    invitation_id: Mapped[UUID] = mapped_column(ForeignKey("form_invitations.id"), unique=True)
    status: Mapped[str] = mapped_column(String(20), default="draft")
    idempotency_key: Mapped[UUID | None] = mapped_column()
    key_id: Mapped[str | None] = mapped_column(String(100))
    nonce: Mapped[bytes | None] = mapped_column(LargeBinary)
    ciphertext: Mapped[bytes | None] = mapped_column(LargeBinary)


class Receipt(Base):
    __tablename__ = "submission_receipts"
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    submission_id: Mapped[UUID] = mapped_column(ForeignKey("form_submissions.id"))
    token_hash: Mapped[bytes] = mapped_column(LargeBinary, unique=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class GuestSession(Base):
    __tablename__ = "guest_sessions"
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    invitation_id: Mapped[UUID] = mapped_column(ForeignKey("form_invitations.id"))
    receipt_id: Mapped[UUID | None] = mapped_column(ForeignKey("submission_receipts.id"))
    token_hash: Mapped[bytes] = mapped_column(LargeBinary, unique=True)
    csrf_hash: Mapped[bytes] = mapped_column(LargeBinary)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class BotContact(Base):
    __tablename__ = "bot_contacts"
    telegram_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False)
    allowed: Mapped[bool] = mapped_column(default=False)


class Delivery(Base):
    __tablename__ = "notification_deliveries"
    __table_args__ = (
        UniqueConstraint("invitation_id", "telegram_id", "kind", name="one_event_delivery"),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    invitation_id: Mapped[UUID] = mapped_column(ForeignKey("form_invitations.id"))
    telegram_id: Mapped[int] = mapped_column(BigInteger)
    status: Mapped[str] = mapped_column(String(32), default="pending")
    kind: Mapped[str] = mapped_column(String(20), default="invitation")
    attempts: Mapped[int] = mapped_column(default=0)
    lease_id: Mapped[UUID | None] = mapped_column()
    lease_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    key_id: Mapped[str | None] = mapped_column(String(100))
    nonce: Mapped[bytes | None] = mapped_column(LargeBinary)
    ciphertext: Mapped[bytes | None] = mapped_column(LargeBinary)
