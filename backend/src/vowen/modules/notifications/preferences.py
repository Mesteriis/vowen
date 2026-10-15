from datetime import UTC, datetime, timedelta
from typing import Literal
from uuid import UUID
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Request
from pydantic import BaseModel, ConfigDict, Field, model_validator
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from vowen.core.errors import AppError
from vowen.modules.auth.router import DB, Member
from vowen.modules.forms.models import BotContact, Delivery
from vowen.modules.identity.models import User, UserPreferences


class NotificationCommand(BaseModel):
    model_config = ConfigDict(extra="forbid")
    channels: list[Literal["in_app", "telegram"]] = Field(max_length=2)
    quiet_enabled: bool
    quiet_start: int = Field(ge=0, le=1439)
    quiet_end: int = Field(ge=0, le=1439)

    @model_validator(mode="after")
    def valid(self) -> "NotificationCommand":
        if len(set(self.channels)) != len(self.channels):
            raise ValueError("Duplicate channel")
        if self.quiet_enabled and self.quiet_start == self.quiet_end:
            raise ValueError("Quiet hours need distinct boundaries")
        return self


class NotificationPatch(NotificationCommand):
    expected_version: int = Field(ge=1)


class NotificationView(NotificationCommand):
    revision: int
    timezone: str
    telegram_connected: bool


def quiet_until(now: datetime, timezone: str, enabled: bool, start: int, end: int) -> datetime:
    if not enabled:
        return now
    zone = ZoneInfo(timezone)

    def boundary(wall: datetime, closing: bool) -> datetime:
        candidates = [wall.replace(tzinfo=zone, fold=f).astimezone(UTC) for f in (0, 1)]
        valid = [c for c in candidates if c.astimezone(zone).replace(tzinfo=None) == wall]
        # Quiet time includes the entire fold; nonexistent boundaries shift forward.
        return max(valid) if closing and valid else min(valid) if valid else max(candidates)

    today = now.astimezone(zone).date()
    for day in (today - timedelta(days=1), today):
        closing_day = day + timedelta(days=int(start > end))
        opening = boundary(datetime(day.year, day.month, day.day, start // 60, start % 60), False)
        closing = boundary(
            datetime(closing_day.year, closing_day.month, closing_day.day, end // 60, end % 60),
            True,
        )
        if opening <= now < closing:
            return closing
    return now


async def allowed_at(db: AsyncSession, uid: UUID, now: datetime) -> datetime:
    p = await db.get(UserPreferences, uid, populate_existing=True)
    if p is None:
        raise AppError(503, "UNAVAILABLE")
    return quiet_until(now, p.timezone, p.quiet_enabled, p.quiet_start, p.quiet_end)


async def channel(db: AsyncSession, uid: UUID, name: str) -> bool:
    p = await db.get(UserPreferences, uid, populate_existing=True)
    return bool(p and name in p.notification_channels)


async def view(db: AsyncSession, uid: UUID) -> NotificationView:
    p = await db.get(UserPreferences, uid, populate_existing=True)
    u = await db.get(User, uid)
    if p is None or u is None:
        raise AppError(503, "UNAVAILABLE")
    contact = await db.get(BotContact, u.telegram_id)
    return NotificationView.model_validate(
        dict(
            channels=p.notification_channels,
            quiet_enabled=p.quiet_enabled,
            quiet_start=p.quiet_start,
            quiet_end=p.quiet_end,
            revision=p.notification_revision,
            timezone=p.timezone,
            telegram_connected=bool(contact and contact.allowed),
        )
    )


router = APIRouter(prefix="/api/v1/me/notifications")


@router.get("", response_model=NotificationView)
async def get(principal: Member, db: DB) -> NotificationView:
    return await view(db, principal.user_id)


@router.patch("", response_model=NotificationView)
async def patch(
    body: NotificationPatch, principal: Member, db: DB, request: Request
) -> NotificationView:
    p = await db.scalar(
        select(UserPreferences)
        .where(UserPreferences.user_id == principal.user_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    assert p is not None
    if p.notification_revision != body.expected_version:
        raise AppError(409, "VERSION_CONFLICT")
    if "telegram" in p.notification_channels and "telegram" not in body.channels:
        p.notification_generation += 1
        from vowen.modules.forms.service import clear
        from vowen.modules.notifications.delivery import suppress_recipient

        await suppress_recipient(db, principal.user_id)
        u = await db.get(User, principal.user_id)
        assert u is not None
        rows = (
            await db.scalars(
                select(Delivery)
                .where(
                    Delivery.telegram_id == u.telegram_id,
                    Delivery.status.in_(["pending", "sending"]),
                )
                .with_for_update()
            )
        ).all()
        for d in rows:
            d.status = "manual_delivery_required"
            clear(d)
    p.notification_channels = list(body.channels)
    p.quiet_enabled, p.quiet_start, p.quiet_end = (
        body.quiet_enabled,
        body.quiet_start,
        body.quiet_end,
    )
    p.notification_revision += 1
    from vowen.modules.notifications.models import MemberDelivery

    await db.execute(
        update(MemberDelivery)
        .where(
            MemberDelivery.user_id == principal.user_id,
            MemberDelivery.status == "pending",
            MemberDelivery.attempts == 0,
        )
        .values(available_at=request.app.state.clock.now())
    )
    u = await db.get(User, principal.user_id)
    assert u is not None
    await db.execute(
        update(Delivery)
        .where(Delivery.telegram_id == u.telegram_id, Delivery.status == "pending")
        .values(deferred_until=None)
    )
    return await view(db, principal.user_id)
