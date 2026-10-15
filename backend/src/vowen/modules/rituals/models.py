from datetime import date, datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    LargeBinary,
    String,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from vowen.core.database import Base


class Ritual(Base):
    __tablename__ = "rituals"
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    author_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"))
    revision: Mapped[int] = mapped_column(default=1)
    current_version_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("ritual_versions.id", use_alter=True, name="current_ritual_version")
    )


class RitualVersion(Base):
    __tablename__ = "ritual_versions"
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    ritual_id: Mapped[UUID] = mapped_column(ForeignKey("rituals.id"))
    status: Mapped[str] = mapped_column(String(20), default="draft")
    key_id: Mapped[str] = mapped_column(String(100))
    nonce: Mapped[bytes] = mapped_column(LargeBinary)
    ciphertext: Mapped[bytes] = mapped_column(LargeBinary)


class RitualAssignment(Base):
    __tablename__ = "ritual_assignments"
    __table_args__ = (
        UniqueConstraint("issuer_id", "idempotency_key", name="one_ritual_assignment_request"),
    )
    idempotency_key: Mapped[UUID]
    request_hash: Mapped[bytes] = mapped_column(LargeBinary)
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    ritual_version_id: Mapped[UUID] = mapped_column(ForeignKey("ritual_versions.id"))
    recipient_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"))
    issuer_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"))
    approval_required: Mapped[bool]
    status: Mapped[str] = mapped_column(String(20), default="active")
    revision: Mapped[int] = mapped_column(default=1)
    current_schedule_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("ritual_schedules.id", use_alter=True, name="current_ritual_schedule")
    )
    watermark: Mapped[date] = mapped_column(Date)


class RitualReviewer(Base):
    __tablename__ = "ritual_reviewers"
    assignment_id: Mapped[UUID] = mapped_column(
        ForeignKey("ritual_assignments.id"), primary_key=True
    )
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), primary_key=True)


class RitualSchedule(Base):
    __tablename__ = "ritual_schedules"
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    assignment_id: Mapped[UUID] = mapped_column(ForeignKey("ritual_assignments.id"))
    starts_on: Mapped[date] = mapped_column(Date)
    ends_on: Mapped[date | None] = mapped_column(Date)
    spec: Mapped[dict[str, object]] = mapped_column(JSONB)


class RitualOccurrence(Base):
    __tablename__ = "ritual_occurrences"
    __table_args__ = (
        UniqueConstraint("assignment_id", "local_day", name="one_ritual_local_slot"),
        CheckConstraint(
            "status IN ('scheduled','submitted','approved','needs_changes',"
            "'missed','skipped','cancelled')"
        ),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    assignment_id: Mapped[UUID] = mapped_column(ForeignKey("ritual_assignments.id"))
    schedule_id: Mapped[UUID] = mapped_column(ForeignKey("ritual_schedules.id"))
    local_day: Mapped[date] = mapped_column(Date)
    due_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(20), default="scheduled")
    revision: Mapped[int] = mapped_column(default=1)


class RitualReport(Base):
    __tablename__ = "ritual_reports"
    __table_args__ = (
        UniqueConstraint("occurrence_id", "idempotency_key", name="one_ritual_report_request"),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    attempt: Mapped[int]
    occurrence_id: Mapped[UUID] = mapped_column(ForeignKey("ritual_occurrences.id"))
    idempotency_key: Mapped[UUID]
    submitted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    decision: Mapped[str | None] = mapped_column(String(20))
    reviewer_id: Mapped[UUID | None] = mapped_column(ForeignKey("users.id"))
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    key_id: Mapped[str] = mapped_column(String(100))
    nonce: Mapped[bytes] = mapped_column(LargeBinary)
    ciphertext: Mapped[bytes] = mapped_column(LargeBinary)


class RitualNotice(Base):
    __tablename__ = "ritual_notices"
    __table_args__ = (UniqueConstraint("event_key", "user_id", name="one_ritual_notice"),)
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    assignment_id: Mapped[UUID] = mapped_column(ForeignKey("ritual_assignments.id"))
    occurrence_id: Mapped[UUID | None] = mapped_column(ForeignKey("ritual_occurrences.id"))
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"))
    event_key: Mapped[str] = mapped_column(String(150))
    kind: Mapped[str] = mapped_column(String(30))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
