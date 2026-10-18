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


class ChangeRequest(Base):
    """A recipient's proposal, pinned to one direct authority agreement and target."""

    __tablename__ = "change_requests"
    __table_args__ = (
        UniqueConstraint("requester_id", "idempotency_key"),
        CheckConstraint(
            "kind IN ('ritual_skip','ritual_pause','rule_add','rule_edit','rule_delete')"
        ),
        CheckConstraint("status IN ('pending','approved','rejected','withdrawn')"),
        CheckConstraint(
            "(kind='rule_add' AND "
            "ritual_assignment_id IS NULL AND "
            "rule_assignment_id IS NULL AND "
            "occurrence_id IS NULL) OR "
            "(kind IN ('rule_edit','rule_delete') AND "
            "rule_assignment_id IS NOT NULL AND "
            "ritual_assignment_id IS NULL AND "
            "occurrence_id IS NULL) OR "
            "(kind='ritual_pause' AND "
            "ritual_assignment_id IS NOT NULL AND "
            "rule_assignment_id IS NULL AND "
            "occurrence_id IS NULL) OR "
            "(kind='ritual_skip' AND "
            "ritual_assignment_id IS NOT NULL AND "
            "occurrence_id IS NOT NULL AND "
            "rule_assignment_id IS NULL)"
        ),
        Index(
            "pending_ritual_request",
            "ritual_assignment_id",
            "kind",
            "occurrence_id",
            unique=True,
            postgresql_where=text("status='pending' AND kind='ritual_skip'"),
        ),
        Index(
            "pending_ritual_pause",
            "ritual_assignment_id",
            unique=True,
            postgresql_where=text("status='pending' AND kind='ritual_pause'"),
        ),
        Index(
            "pending_rule_request",
            "rule_assignment_id",
            unique=True,
            postgresql_where=text("status='pending' AND rule_assignment_id IS NOT NULL"),
        ),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    kind: Mapped[str] = mapped_column(String(20))
    requester_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"))
    approver_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"))
    relation_id: Mapped[UUID] = mapped_column(ForeignKey("authority_relations.id"))
    relation_version_id: Mapped[UUID] = mapped_column(ForeignKey("relation_versions.id"))
    ritual_assignment_id: Mapped[UUID | None] = mapped_column(ForeignKey("ritual_assignments.id"))
    rule_assignment_id: Mapped[UUID | None] = mapped_column(ForeignKey("rule_assignments.id"))
    occurrence_id: Mapped[UUID | None] = mapped_column(ForeignKey("ritual_occurrences.id"))
    target_revision: Mapped[int | None]
    assignment_revision: Mapped[int | None]
    rule_revision: Mapped[int | None]
    rule_version_id: Mapped[UUID | None] = mapped_column(ForeignKey("rule_versions.id"))
    result_assignment_id: Mapped[UUID | None] = mapped_column(ForeignKey("rule_assignments.id"))
    idempotency_key: Mapped[UUID]
    request_hash: Mapped[bytes] = mapped_column(LargeBinary)
    status: Mapped[str] = mapped_column(String(20), default="pending")
    revision: Mapped[int] = mapped_column(default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    decision_actor_id: Mapped[UUID | None] = mapped_column(ForeignKey("users.id"))
    key_id: Mapped[str] = mapped_column(String(100))
    nonce: Mapped[bytes] = mapped_column(LargeBinary)
    ciphertext: Mapped[bytes] = mapped_column(LargeBinary)
