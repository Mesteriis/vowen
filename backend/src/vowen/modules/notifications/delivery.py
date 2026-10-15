"""Fenced neutral delivery. An ambiguous send is never automatically repeated."""

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import datetime, timedelta
from uuid import UUID, uuid4

from sqlalchemy import case, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy.sql.elements import ColumnElement

from vowen.core.clock import Clock
from vowen.modules.forms.models import BotContact
from vowen.modules.identity.models import User, UserPreferences
from vowen.modules.notifications.models import MemberDelivery
from vowen.modules.relations.models import Relation
from vowen.modules.rewards.models import RewardGrant, RewardNotice
from vowen.modules.rituals import service as rituals
from vowen.modules.rituals.models import RitualAssignment, RitualNotice, RitualOccurrence


@dataclass(frozen=True)
class Claim:
    id: UUID
    lease_id: UUID


@dataclass(frozen=True)
class Destination:
    telegram_id: int
    language: str
    consent_generation: int
    notification_generation: int = 0


async def destination(db: AsyncSession, uid: UUID) -> Destination | None:
    user = await db.get(User, uid, populate_existing=True)
    contact = await db.get(BotContact, user.telegram_id, populate_existing=True) if user else None
    if not user or not user.is_active or user.paused or not contact or not contact.allowed:
        return None
    preferences = await db.get(UserPreferences, uid, populate_existing=True)
    if preferences is None or "telegram" not in preferences.notification_channels:
        return None
    return Destination(
        user.telegram_id,
        preferences.language,
        contact.delivery_generation,
        preferences.notification_generation,
    )


async def enqueue(
    db: AsyncSession,
    uid: UUID,
    now: datetime,
    *,
    ritual_notice_id: UUID | None = None,
    reward_notice_id: UUID | None = None,
    occurrence_revision: int | None = None,
) -> None:
    target = await destination(db, uid)
    row = MemberDelivery(
        user_id=uid,
        ritual_notice_id=ritual_notice_id,
        reward_notice_id=reward_notice_id,
        occurrence_revision=occurrence_revision,
        created_at=now,
        available_at=now,
        status="pending" if target else "suppressed",
        consent_generation=target.consent_generation if target else 0,
        notification_generation=target.notification_generation if target else 0,
    )
    row.authority_versions = await authority_versions(db, row)
    db.add(row)


async def authority_versions(db: AsyncSession, d: MemberDelivery) -> dict[str, int]:
    # Revocation/version changes can commit while the event/outbox is still invisible.
    # Record the applicable direct relation revisions so a later restoration cannot
    # authorize an event queued under the old interval. No transitive relations.
    actors = {d.user_id}
    if d.ritual_notice_id:
        n = await db.get(RitualNotice, d.ritual_notice_id)
        a = await db.get(RitualAssignment, n.assignment_id) if n else None
        if a is None:
            return {}
        actors.add(a.issuer_id)
        recipient_id = a.recipient_id
    else:
        rn = await db.get(RewardNotice, d.reward_notice_id)
        g = await db.get(RewardGrant, rn.grant_id) if rn else None
        if g is None:
            return {}
        actors.add(g.issuer_id)
        recipient_id = g.recipient_id
    rows = (
        await db.execute(
            select(Relation.id, Relation.version).where(
                Relation.dominant_user_id.in_(actors),
                Relation.submissive_user_id == recipient_id,
            )
        )
    ).all()
    return {str(rid): revision for rid, revision in rows}


async def authorized(db: AsyncSession, d: MemberDelivery, now: datetime) -> Destination | None:
    target = await destination(db, d.user_id)
    if (
        target is None
        or d.cancellation_requested
        or target.consent_generation != d.consent_generation
        or target.notification_generation != d.notification_generation
        or now >= d.created_at + timedelta(hours=24)
    ):
        return None
    if d.ritual_notice_id:
        n = await db.get(RitualNotice, d.ritual_notice_id)
        a = await db.get(RitualAssignment, n.assignment_id) if n else None
        if not n or n.user_id != d.user_id or not a or not await rituals.effective(db, a):
            return None
        if not await rituals.visible(db, a, d.user_id):
            return None
        if n.occurrence_id:
            o = await db.get(RitualOccurrence, n.occurrence_id)
            if not o or o.revision != d.occurrence_revision:
                return None
            if n.kind == "due" and (o.status != "scheduled" or not o.due_at <= now < o.expires_at):
                return None
    elif d.reward_notice_id:
        rn = await db.get(RewardNotice, d.reward_notice_id)
        g = await db.get(RewardGrant, rn.grant_id) if rn else None
        if (
            not rn
            or rn.user_id != d.user_id
            or not g
            or g.revision != rn.revision
            or d.user_id not in {g.issuer_id, g.recipient_id}
        ):
            return None
        if not await rituals.scoped(
            db, g.issuer_id, g.recipient_id, "rewards.grant", {g.issuer_id}
        ):
            return None
    else:
        return None
    if d.authority_versions != await authority_versions(db, d):
        return None
    return target


def finish(d: MemberDelivery, status: str) -> None:
    d.status, d.lease_id, d.lease_until = status, None, None


async def claim(db: AsyncSession, now: datetime) -> Claim | None:
    for _ in range(20):
        d = await db.scalar(
            select(MemberDelivery)
            .where(
                MemberDelivery.status.in_(["pending", "claimed", "sending"]),
                MemberDelivery.available_at <= now,
                or_(MemberDelivery.lease_until.is_(None), MemberDelivery.lease_until <= now),
            )
            .order_by(MemberDelivery.created_at, MemberDelivery.id)
            .with_for_update(skip_locked=True)
            .limit(1)
        )
        if d is None:
            break
        if d.status == "sending":
            finish(d, "uncertain")
        elif d.attempts >= 3:
            finish(d, "manual_delivery_required")
        elif await authorized(db, d, now) is None:
            finish(d, "suppressed")
        else:
            from vowen.modules.notifications.preferences import allowed_at

            available = await allowed_at(db, d.user_id, now)
            if available > now:
                d.available_at = available
                finish(d, "pending")
                continue
            d.status, d.lease_id, d.lease_until = "claimed", uuid4(), now + timedelta(minutes=1)
            return Claim(d.id, d.lease_id)
    return None


async def leased(
    db: AsyncSession, task: Claim, status: str, now: datetime
) -> MemberDelivery | None:
    d = await db.get(MemberDelivery, task.id, with_for_update=True)
    return (
        d
        if (
            d
            and d.status == status
            and d.lease_id == task.lease_id
            and d.lease_until
            and d.lease_until > now
        )
        else None
    )


async def prepare(db: AsyncSession, task: Claim, now: datetime) -> Destination | None:
    d = await leased(db, task, "claimed", now)
    if d is None:
        return None
    target = await authorized(db, d, now)
    if target is None:
        finish(d, "suppressed")
        return None
    from vowen.modules.notifications.preferences import allowed_at

    available = await allowed_at(db, d.user_id, now)
    if available > now:
        finish(d, "pending")
        d.available_at = available
        return None
    d.status, d.attempts = "sending", d.attempts + 1
    d.lease_until = now + timedelta(minutes=1)
    return target


async def complete(
    db: AsyncSession,
    task: Claim,
    outcome: str,
    now: datetime,
    retry_after: int = 60,
) -> bool:
    d = await leased(db, task, "sending", now)
    if d is None:
        return False
    if outcome == "retry" and d.cancellation_requested:
        finish(d, "suppressed")
    elif outcome == "retry" and d.attempts < 3:
        finish(d, "pending")
        d.available_at = now + timedelta(seconds=max(1, retry_after))
    else:
        finish(d, "manual_delivery_required" if outcome in {"retry", "blocked"} else outcome)
    if outcome == "blocked":
        user = await db.get(User, d.user_id)
        contact = (
            await db.get(BotContact, user.telegram_id, populate_existing=True) if user else None
        )
        if contact:
            contact.allowed = False
            contact.delivery_generation += 1
    return True


async def deliver_one(
    sessions: async_sessionmaker[AsyncSession],
    base_url: str,
    send: Callable[[int, str], Awaitable[None]],
) -> bool:
    async with sessions() as db, db.begin():
        task = await claim(db, Clock().now())
    if task is None:
        return False
    # Separate session: re-read opt-in, identity, pause, scopes and event freshness.
    async with sessions() as db, db.begin():
        target = await prepare(db, task, Clock().now())
    if target is None:
        return True
    text = (
        "У вас есть обновление в приложении"
        if target.language == "ru"
        else "You have an update in the app"
    )
    outcome, retry_after = "uncertain", 60
    try:
        # No DB transaction, content, names, evidence, identifiers or bearer links.
        await send(target.telegram_id, text + "\n" + base_url.rstrip("/") + "/")
        outcome = "delivered"
    except Exception as error:
        from aiogram.exceptions import (
            TelegramBadRequest,
            TelegramForbiddenError,
            TelegramRetryAfter,
        )

        if isinstance(error, TelegramRetryAfter):
            outcome, retry_after = "retry", error.retry_after
        elif isinstance(error, TelegramForbiddenError):
            outcome = "blocked"
        elif isinstance(error, TelegramBadRequest):
            outcome = "manual_delivery_required"
        # Other transport/server failures may have accepted the request. Never log them.
    async with sessions() as db, db.begin():
        await complete(db, task, outcome, Clock().now(), retry_after)
    return True


async def cancel_where(db: AsyncSession, condition: ColumnElement[bool]) -> None:
    sending = MemberDelivery.status == "sending"
    await db.execute(
        update(MemberDelivery)
        .where(
            MemberDelivery.status.in_(["pending", "claimed", "sending"]),
            condition,
        )
        .values(
            cancellation_requested=True,
            status=case((sending, MemberDelivery.status), else_="suppressed"),
            lease_id=case((sending, MemberDelivery.lease_id), else_=None),
            lease_until=case((sending, MemberDelivery.lease_until), else_=None),
        )
    )


async def suppress_recipient(db: AsyncSession, uid: UUID) -> None:
    await cancel_where(db, MemberDelivery.user_id == uid)


async def suppress_assignment(db: AsyncSession, aid: UUID) -> None:
    notices = select(RitualNotice.id).where(RitualNotice.assignment_id == aid)
    await cancel_where(db, MemberDelivery.ritual_notice_id.in_(notices))


async def suppress_scope(
    db: AsyncSession,
    actor_id: UUID | None = None,
    target_id: UUID | None = None,
) -> None:
    """Persist denial even if consent is restored before the next worker tick."""
    from sqlalchemy import and_

    if actor_id is not None and target_id is not None:
        ritual_match = and_(
            RitualAssignment.recipient_id == target_id,
            or_(RitualAssignment.issuer_id == actor_id, RitualNotice.user_id == actor_id),
        )
        reward_match = and_(
            RewardGrant.issuer_id == actor_id, RewardGrant.recipient_id == target_id
        )
    else:
        uid = actor_id or target_id
        assert uid is not None
        ritual_match = or_(
            RitualAssignment.issuer_id == uid,
            RitualAssignment.recipient_id == uid,
            RitualNotice.user_id == uid,
        )
        reward_match = or_(
            RewardGrant.issuer_id == uid,
            RewardGrant.recipient_id == uid,
            RewardNotice.user_id == uid,
        )
    ritual_ids = select(RitualNotice.id).join(RitualAssignment).where(ritual_match)
    reward_ids = select(RewardNotice.id).join(RewardGrant).where(reward_match)
    await cancel_where(
        db,
        or_(
            MemberDelivery.ritual_notice_id.in_(ritual_ids),
            MemberDelivery.reward_notice_id.in_(reward_ids),
        ),
    )
