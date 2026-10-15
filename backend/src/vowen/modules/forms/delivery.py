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


async def claim_delivery(
    db: AsyncSession, now: datetime, cipher: PayloadCipher
) -> ClaimedDelivery | None:
    rows = (
        await db.scalars(
            select(Delivery)
            .where(
                Delivery.status.in_(["pending", "sending"]),
                or_(Delivery.lease_until.is_(None), Delivery.lease_until <= now),
            )
            .order_by(Delivery.id)
            .with_for_update(skip_locked=True)
            .limit(20)
        )
    ).all()
    for d in rows:
        i = await db.get(Invitation, d.invitation_id)
        contact = await db.get(BotContact, d.telegram_id)
        recipient = await db.scalar(select(User).where(User.telegram_id == d.telegram_id))
        authorized = True
        if d.kind == "response":
            response = await db.scalar(
                select(Submission).where(Submission.invitation_id == d.invitation_id)
            )
            reader = (
                await db.get(InvitationReader, (d.invitation_id, recipient.id))
                if recipient
                else None
            )
            authorized = bool(
                response
                and response.status == "submitted"
                and reader
                and recipient
                and recipient.is_active
                and not recipient.paused
            )
        elif recipient:
            authorized = recipient.is_active and not recipient.paused
        if (
            not authorized
            or i is None
            or (d.kind == "invitation" and (i.revoked_at or i.expires_at <= now))
            or (i.retention_until is not None and i.retention_until <= now)
            or contact is None
            or not contact.allowed
            or d.attempts >= 3
        ):
            d.status = "manual_delivery_required"
            clear(d)
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
