from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, LargeBinary, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from vowen.core.database import Base


class DisciplineRecord(Base):
    __tablename__ = "discipline_records"
    __table_args__ = (UniqueConstraint("author_id", "idempotency_key"),)
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    author_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"))
    recipient_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"))
    idempotency_key: Mapped[UUID]
    current_version_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("discipline_versions.id", use_alter=True, name="current_discipline_version")
    )
    revision: Mapped[int] = mapped_column(default=1)
    status: Mapped[str] = mapped_column(String(20), default="proposed")


class DisciplineVersion(Base):
    __tablename__ = "discipline_versions"
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    record_id: Mapped[UUID] = mapped_column(ForeignKey("discipline_records.id"))
    rule_version_id: Mapped[UUID | None] = mapped_column(ForeignKey("rule_versions.id"))
    occurrence_id: Mapped[UUID | None] = mapped_column(ForeignKey("ritual_occurrences.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    key_id: Mapped[str] = mapped_column(String(100))
    nonce: Mapped[bytes] = mapped_column(LargeBinary)
    ciphertext: Mapped[bytes] = mapped_column(LargeBinary)


class DisciplineReviewer(Base):
    __tablename__ = "discipline_reviewers"
    record_id: Mapped[UUID] = mapped_column(ForeignKey("discipline_records.id"), primary_key=True)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), primary_key=True)


class DisciplineTransition(Base):
    __tablename__ = "discipline_transitions"
    __table_args__ = (UniqueConstraint("record_id", "revision"),)
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    record_id: Mapped[UUID] = mapped_column(ForeignKey("discipline_records.id"))
    version_id: Mapped[UUID] = mapped_column(ForeignKey("discipline_versions.id"))
    revision: Mapped[int]
    status: Mapped[str] = mapped_column(String(20))
    actor_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    key_id: Mapped[str] = mapped_column(String(100))
    nonce: Mapped[bytes] = mapped_column(LargeBinary)
    ciphertext: Mapped[bytes] = mapped_column(LargeBinary)
