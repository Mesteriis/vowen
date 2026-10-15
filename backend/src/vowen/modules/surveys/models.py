from datetime import date, datetime
from uuid import UUID, uuid4

from pydantic import JsonValue
from sqlalchemy import DateTime, ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from vowen.core.database import Base


class SurveySchedule(Base):
    __tablename__ = "survey_schedules"
    __table_args__ = (UniqueConstraint("author_id", "idempotency_key"),)
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    author_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"))
    recipient_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"))
    form_version_id: Mapped[UUID] = mapped_column(ForeignKey("form_versions.id"))
    idempotency_key: Mapped[UUID]
    config: Mapped[dict[str, JsonValue]] = mapped_column(JSONB)
    ritual_assignment_id: Mapped[UUID | None] = mapped_column(ForeignKey("ritual_assignments.id"))
    source_revision: Mapped[int | None]
    authority_revision: Mapped[int | None]
    revision: Mapped[int] = mapped_column(default=1)
    owner_paused: Mapped[bool] = mapped_column(default=False)
    recipient_paused: Mapped[bool] = mapped_column(default=False)
    blocked_through: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    checked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    watermark: Mapped[date | None]


class SurveyWave(Base):
    __tablename__ = "survey_waves"
    __table_args__ = (
        UniqueConstraint("schedule_id", "event_key"),
        Index("survey_wave_invitation", "invitation_id"),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    schedule_id: Mapped[UUID] = mapped_column(ForeignKey("survey_schedules.id"))
    event_key: Mapped[str] = mapped_column(String(100))
    due_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    occurrence_id: Mapped[UUID | None] = mapped_column(ForeignKey("ritual_occurrences.id"))
    invitation_id: Mapped[UUID | None] = mapped_column(ForeignKey("form_invitations.id"))
    status: Mapped[str] = mapped_column(String(20))
    reason: Mapped[str | None] = mapped_column(String(40))
