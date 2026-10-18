from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import BigInteger, Boolean, CheckConstraint, DateTime, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from vowen.core.database import Base


class User(Base):
    __tablename__ = "users"
    __table_args__ = (CheckConstraint("telegram_id > 0", name="positive_telegram_id"),)
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True)
    display_name: Mapped[str] = mapped_column(String(100))
    shop_role: Mapped[str] = mapped_column(String(20), default="viewer")
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    paused: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class UserPreferences(Base):
    __tablename__ = "user_preferences"
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), primary_key=True)
    language: Mapped[str] = mapped_column(String(2), default="en")
    timezone: Mapped[str] = mapped_column(String(64), default="UTC")
    profile_labels: Mapped[list[str]] = mapped_column(JSONB, default=list)
    profile_version: Mapped[int] = mapped_column(default=1)
    notification_channels: Mapped[list[str]] = mapped_column(
        JSONB, default=lambda: ["in_app", "telegram"]
    )
    notification_revision: Mapped[int] = mapped_column(default=1)
    notification_generation: Mapped[int] = mapped_column(default=0)
    quiet_enabled: Mapped[bool] = mapped_column(default=False)
    quiet_start: Mapped[int] = mapped_column(default=1320)
    quiet_end: Mapped[int] = mapped_column(default=480)


class AdministrationState(Base):
    __tablename__ = "administration_state"
    __table_args__ = (CheckConstraint("id = 1", name="singleton_administration"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    revision: Mapped[int] = mapped_column(default=1)


class AdministratorEvent(Base):
    __tablename__ = "administrator_events"
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    actor_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"))
    target_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"))
    action: Mapped[str] = mapped_column(String(16))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
