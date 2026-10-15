"""Neutral member notifications; separate from guest form capability delivery."""

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from vowen.core.database import Base


class MemberDelivery(Base):
    __tablename__ = "member_deliveries"
    __table_args__ = (
        CheckConstraint("(ritual_notice_id IS NULL) <> (reward_notice_id IS NULL)"),
        CheckConstraint("attempts BETWEEN 0 AND 3"),
        CheckConstraint(
            "status IN ('pending','claimed','sending','delivered','suppressed',"
            "'uncertain','manual_delivery_required')"
        ),
        Index("member_delivery_ready", "status", "available_at"),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"))
    ritual_notice_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("ritual_notices.id"), unique=True
    )
    reward_notice_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("reward_notices.id"), unique=True
    )
    notification_generation: Mapped[int] = mapped_column(default=0, server_default="0")
    consent_generation: Mapped[int] = mapped_column(default=0, server_default="0")
    cancellation_requested: Mapped[bool] = mapped_column(default=False, server_default="false")
    authority_versions: Mapped[dict[str, int]] = mapped_column(
        JSONB, default=dict, server_default="{}"
    )
    occurrence_revision: Mapped[int | None]
    status: Mapped[str] = mapped_column(String(32), default="pending")
    attempts: Mapped[int] = mapped_column(default=0)
    lease_id: Mapped[UUID | None]
    lease_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    available_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
