from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    LargeBinary,
    String,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from vowen.core.database import Base


class Rule(Base):
    __tablename__ = "rules"
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    author_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"))
    revision: Mapped[int] = mapped_column(default=1)
    current_version_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("rule_versions.id", use_alter=True, name="current_rule_version")
    )


class RuleVersion(Base):
    __tablename__ = "rule_versions"
    __table_args__ = (CheckConstraint("status IN ('draft','published','archived')"),)
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    rule_id: Mapped[UUID] = mapped_column(ForeignKey("rules.id"))
    status: Mapped[str] = mapped_column(String(20), default="draft")
    key_id: Mapped[str] = mapped_column(String(100))
    nonce: Mapped[bytes] = mapped_column(LargeBinary)
    ciphertext: Mapped[bytes] = mapped_column(LargeBinary)


class RuleAssignment(Base):
    __tablename__ = "rule_assignments"
    __table_args__ = (
        UniqueConstraint("rule_version_id", "recipient_id", name="one_rule_version_recipient"),
        Index(
            "one_active_rule_recipient",
            "rule_id",
            "recipient_id",
            unique=True,
            postgresql_where=text("status='active'"),
        ),
        CheckConstraint("status IN ('pending_acceptance','active','paused','revoked')"),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    rule_id: Mapped[UUID] = mapped_column(ForeignKey("rules.id"))
    rule_version_id: Mapped[UUID] = mapped_column(ForeignKey("rule_versions.id"))
    recipient_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"))
    issuer_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"))
    revision: Mapped[int] = mapped_column(default=1)
    status: Mapped[str] = mapped_column(String(24), default="pending_acceptance")
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class RuleManager(Base):
    __tablename__ = "rule_assignment_managers"
    assignment_id: Mapped[UUID] = mapped_column(ForeignKey("rule_assignments.id"), primary_key=True)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), primary_key=True)
