import asyncio
import logging
import signal
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from sqlalchemy import Date, exists, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from vowen.core.clock import Clock
from vowen.core.config import Settings
from vowen.core.crypto import PayloadCipher
from vowen.core.database import check_schema, engine_for, sessions_for
from vowen.modules.identity.models import User
from vowen.modules.relations.models import Relation, RelationVersion
from vowen.modules.rituals import service as rituals
from vowen.modules.rituals.models import (
    RitualAssignment,
    RitualNotice,
    RitualOccurrence,
    RitualSchedule,
)
from vowen.modules.rituals.schedule import local_slot, slot_days
from vowen.modules.rituals.schemas import Schedule
from vowen.modules.surveys.service import generate as generate_surveys


async def generate_assignment(
    db: AsyncSession, a: RitualAssignment, now: datetime, days_limit: int
) -> None:
    schedules = (
        await db.scalars(
            select(RitualSchedule)
            .where(RitualSchedule.assignment_id == a.id)
            .order_by(RitualSchedule.starts_on)
        )
    ).all()
    current = next(s for s in schedules if s.id == a.current_schedule_id)
    today = now.astimezone(ZoneInfo(str(current.spec["timezone"]))).date()
    live = await rituals.effective(db, a)
    slots = (
        await db.scalars(
            select(RitualOccurrence)
            .where(
                RitualOccurrence.assignment_id == a.id,
                RitualOccurrence.status.in_(["scheduled", "needs_changes"]),
            )
            .with_for_update()
        )
    ).all()
    for o in slots:
        if not live:
            o.status = "cancelled"
            o.revision += 1
        elif o.expires_at <= now:
            o.status = "missed"
            o.revision += 1
        elif o.status == "scheduled" and o.due_at <= now and o.local_day == today:
            await rituals.notice(db, a, [a.recipient_id], "due", now, o)
    if not live:
        a.watermark = max(a.watermark, today + timedelta(days=1))
        return
    end = min(today, a.watermark + timedelta(days=days_limit - 1))
    for s in schedules:
        spec = Schedule.model_validate(s.spec)
        for day in slot_days(spec, max(a.watermark, s.starts_on), min(end, s.ends_on or date.max)):
            existing = await db.scalar(
                select(RitualOccurrence.id).where(
                    RitualOccurrence.assignment_id == a.id, RitualOccurrence.local_day == day
                )
            )
            if existing is not None:
                continue
            due = local_slot(day, spec.hour, spec.minute, spec.timezone)
            expires = due + timedelta(hours=spec.window_hours)
            o = RitualOccurrence(
                reward_policy_id=a.reward_policy_id,
                assignment_id=a.id,
                schedule_id=s.id,
                local_day=day,
                due_at=due,
                expires_at=expires,
                status="missed" if expires <= now else "scheduled",
            )
            db.add(o)
            await db.flush()
            if due <= now < expires and day == today:
                await rituals.notice(db, a, [a.recipient_id], "due", now, o)
    if end >= a.watermark:
        a.watermark = end + timedelta(days=1)


async def generate(
    db: AsyncSession, now: datetime, days_limit: int = 31, assignment_limit: int = 50
) -> None:
    # Fairness: only assignments with unprocessed days, expiries, or undelivered due
    # notices are eligible; a completed first page cannot starve the rest.
    local_today = func.cast(func.timezone(RitualSchedule.spec["timezone"].astext, now), Date)
    unavailable = (
        exists(
            select(User.id).where(
                User.id.in_([RitualAssignment.issuer_id, RitualAssignment.recipient_id]),
                (User.paused | ~User.is_active),
            )
        )
        | ~exists(
            select(Relation.id)
            .join(RelationVersion, RelationVersion.id == Relation.relation_version_id)
            .where(
                Relation.dominant_user_id == RitualAssignment.issuer_id,
                Relation.submissive_user_id == RitualAssignment.recipient_id,
                Relation.status == "active",
                RelationVersion.scopes.contains(["rituals.assign"]),
            )
        )
        | (RitualAssignment.status != "active")
    )
    pending = exists(
        select(RitualOccurrence.id).where(
            RitualOccurrence.assignment_id == RitualAssignment.id,
            RitualOccurrence.status.in_(["scheduled", "needs_changes"]),
            or_(
                unavailable,
                RitualOccurrence.expires_at <= now,
                (RitualOccurrence.due_at <= now)
                & (RitualOccurrence.local_day == local_today)
                & ~exists(
                    select(RitualNotice.id).where(
                        RitualNotice.occurrence_id == RitualOccurrence.id,
                        RitualNotice.kind == "due",
                    )
                ),
            ),
        )
    )
    rows = (
        await db.scalars(
            select(RitualAssignment)
            .join(RitualSchedule, RitualAssignment.current_schedule_id == RitualSchedule.id)
            .where(
                RitualAssignment.status != "revoked",
                or_(RitualAssignment.watermark <= local_today, pending),
            )
            .order_by(RitualAssignment.watermark, RitualAssignment.id)
            .limit(assignment_limit)
            .with_for_update(of=RitualAssignment, skip_locked=True)
        )
    ).all()
    for a in rows:
        await generate_assignment(db, a, now, days_limit)


async def run() -> None:
    settings = Settings()
    engine = engine_for(settings.database_url)
    stop = asyncio.Event()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, stop.set)
    try:
        while not stop.is_set():
            try:
                if not await check_schema(engine):
                    raise RuntimeError("Schema unavailable")
                async with sessions_for(engine)() as db, db.begin():
                    await generate(db, Clock().now())
                async with sessions_for(engine)() as db, db.begin():
                    await generate_surveys(
                        db,
                        Clock().now(),
                        PayloadCipher(settings.data_keyring_file),
                        settings.public_base_url,
                    )
                Path("/tmp/worker-heartbeat").touch()
            except Exception:
                logging.getLogger("vowen").warning("Workspace scheduling unavailable")
            try:
                await asyncio.wait_for(stop.wait(), timeout=15)
            except TimeoutError:
                pass
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(run())
