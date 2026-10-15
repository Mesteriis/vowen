"""Transactional outbox: bounded at-least-once delivery of neutral notifications."""

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import datetime, timedelta
from uuid import UUID, uuid4

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from vowen.core.clock import Clock
from vowen.core.crypto import PayloadCipher
from vowen.modules.forms.models import (
    BotContact,
    Delivery,
    Invitation,
    InvitationReader,
    Submission,
)
from vowen.modules.forms.service import clear, opened
from vowen.modules.identity.models import User


@dataclass(frozen=True)
class ClaimedDelivery:
    id: UUID
    lease_id: UUID
    telegram_id: int
    link: str


async def available_at(db: AsyncSession, d: Delivery, now: datetime) -> datetime | None:
    from vowen.modules.identity.models import UserPreferences
    from vowen.modules.notifications.preferences import allowed_at

    i = await db.get(Invitation, d.invitation_id)
    contact = await db.get(BotContact, d.telegram_id, populate_existing=True)
    recipient = await db.scalar(
        select(User)
        .where(User.telegram_id == d.telegram_id)
        .execution_options(populate_existing=True)
    )
    creator = await db.get(User, i.creator_id, populate_existing=True) if i else None
    if (
        i is None
        or not creator
        or not creator.is_active
        or creator.paused
        or not contact
        or not contact.allowed
        or contact.delivery_generation != d.consent_generation
        or (d.kind == "invitation" and (i.revoked_at or i.expires_at <= now))
        or (i.retention_until is not None and i.retention_until <= now)
    ):
        return None
    if recipient:
        p = await db.get(UserPreferences, recipient.id, populate_existing=True)
        if (
            not recipient.is_active
            or recipient.paused
            or p is None
            or "telegram" not in p.notification_channels
            or p.notification_generation != d.notification_generation
        ):
            return None
    if d.kind == "invitation":
        from vowen.modules.surveys.models import SurveySchedule, SurveyWave
        from vowen.modules.surveys.service import source_effective

        plan = await db.scalar(
            select(SurveySchedule)
            .join(SurveyWave, SurveyWave.schedule_id == SurveySchedule.id)
            .where(SurveyWave.invitation_id == d.invitation_id)
        )
        if plan and (
            plan.owner_paused or plan.recipient_paused or not await source_effective(db, plan)
        ):
            return None
    if d.kind == "response":
        response = await db.scalar(select(Submission).where(Submission.invitation_id == i.id))
        reader = await db.get(InvitationReader, (i.id, recipient.id)) if recipient else None
        if not response or response.status != "submitted" or not reader:
            return None
    elif recipient and i.recipient_user_id is not None and i.recipient_user_id != recipient.id:
        return None
    return await allowed_at(db, recipient.id, now) if recipient else now


async def claim_delivery(
    db: AsyncSession, now: datetime, cipher: PayloadCipher
) -> ClaimedDelivery | None:
    rows = (
        await db.scalars(
            select(Delivery)
            .where(
                Delivery.status.in_(["pending", "sending"]),
                or_(Delivery.lease_until.is_(None), Delivery.lease_until <= now),
                or_(Delivery.deferred_until.is_(None), Delivery.deferred_until <= now),
            )
            .order_by(Delivery.id)
            .with_for_update(skip_locked=True)
            .limit(20)
        )
    ).all()
    for d in rows:
        available = await available_at(db, d, now)
        if available is None or d.attempts >= 3:
            d.status = "manual_delivery_required"
            clear(d)
            continue
        if available > now:
            d.status = "pending"
            d.deferred_until = available
            continue
        d.status, d.attempts = "sending", d.attempts + 1
        d.lease_id, d.lease_until = uuid4(), now + timedelta(minutes=1)
        link = opened(d, cipher).get("link")
        if not isinstance(link, str):
            d.status = "manual_delivery_required"
            clear(d)
            continue
        return ClaimedDelivery(d.id, d.lease_id, d.telegram_id, link)
    return None


async def prepare_delivery(db: AsyncSession, task: ClaimedDelivery, now: datetime) -> bool:
    d = await db.get(Delivery, task.id, with_for_update=True)
    if (
        not d
        or d.status != "sending"
        or d.lease_id != task.lease_id
        or not d.lease_until
        or d.lease_until <= now
    ):
        return False
    available = await available_at(db, d, now)
    if available is None:
        d.status = "manual_delivery_required"
        clear(d)
        return False
    if available > now:
        d.status = "pending"
        d.deferred_until = available
        d.lease_until = None
        d.attempts -= 1
        return False
    return True


async def complete_delivery(
    db: AsyncSession, did: UUID, lease_id: UUID, success: bool, now: datetime, blocked: bool = False
) -> bool:
    d = await db.get(Delivery, did, with_for_update=True)
    if d is None or d.status != "sending" or d.lease_id != lease_id:
        return False
    if success or blocked or d.attempts >= 3:
        d.status = "delivered" if success else "manual_delivery_required"
        clear(d)
        if blocked:
            contact = await db.get(BotContact, d.telegram_id)
            if contact:
                contact.allowed = False
                contact.delivery_generation += 1
    else:
        d.status, d.lease_until = "pending", now + timedelta(minutes=1)
    return True


async def deliver_one(
    sessions: async_sessionmaker[AsyncSession],
    cipher: PayloadCipher,
    send: Callable[[int, str], Awaitable[None]],
) -> bool:
    async with sessions() as db, db.begin():
        task = await claim_delivery(db, Clock().now(), cipher)
    if task is None:
        return False
    async with sessions() as db, db.begin():
        if not await prepare_delivery(db, task, Clock().now()):
            return True
    success, blocked = False, False
    try:
        # No form titles, questions, answers or Telegram parse mode.
        await send(task.telegram_id, "You have an update / У вас есть обновление\n" + task.link)
        success = True
    except Exception as error:
        from aiogram.exceptions import TelegramForbiddenError

        blocked = isinstance(error, TelegramForbiddenError)
        # Never log exceptions: bot URLs and payloads can contain credentials.
    async with sessions() as db, db.begin():
        await complete_delivery(db, task.id, task.lease_id, success, Clock().now(), blocked)
    return True
