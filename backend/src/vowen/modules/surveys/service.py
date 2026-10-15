from datetime import datetime, timedelta
from uuid import UUID, uuid4

from sqlalchemy import exists, select
from sqlalchemy.ext.asyncio import AsyncSession

from vowen.core.crypto import PayloadCipher
from vowen.core.errors import AppError
from vowen.modules.forms.models import FormVersion, Invitation
from vowen.modules.forms.schemas import InvitationCreate
from vowen.modules.forms.service import invite
from vowen.modules.identity.models import User
from vowen.modules.relations.models import Relation
from vowen.modules.rituals import service as rituals
from vowen.modules.rituals.models import RitualAssignment, RitualNotice
from vowen.modules.rituals.schedule import local_slot, slot_days
from vowen.modules.surveys.models import SurveySchedule, SurveyWave
from vowen.modules.surveys.schemas import SurveyCreate, SurveyView, WaveView


def command(p: SurveySchedule) -> SurveyCreate:
    return SurveyCreate.model_validate({**p.config, "idempotency_key": p.idempotency_key})


async def source_effective(db: AsyncSession, p: SurveySchedule) -> bool:
    version = await db.get(FormVersion, p.form_version_id, populate_existing=True)
    if version is None or version.status != "published":
        return False
    if p.ritual_assignment_id is None:
        return True
    a = await db.get(RitualAssignment, p.ritual_assignment_id, populate_existing=True)
    r = await db.scalar(
        select(Relation).where(
            Relation.dominant_user_id == p.author_id,
            Relation.submissive_user_id == p.recipient_id,
            Relation.status == "active",
        )
    )
    return bool(
        a
        and a.issuer_id == p.author_id
        and a.recipient_id == p.recipient_id
        and a.revision == p.source_revision
        and r
        and r.version == p.authority_revision
        and await rituals.effective(db, a)
    )


async def view(db: AsyncSession, p: SurveySchedule) -> SurveyView:
    v = await db.get(FormVersion, p.form_version_id)
    assert v is not None
    return SurveyView(
        id=p.id,
        author_id=p.author_id,
        revision=p.revision,
        owner_paused=p.owner_paused,
        recipient_paused=p.recipient_paused,
        title=str(v.schema_body["title"]),
        source_effective=await source_effective(db, p),
        **command(p).model_dump(),
    )


def wave_view(w: SurveyWave) -> WaveView:
    return WaveView(
        id=w.id,
        due_at=w.due_at,
        occurrence_id=w.occurrence_id,
        invitation_id=w.invitation_id,
        status=w.status,
        reason=w.reason,
    )


async def loaded(db: AsyncSession, pid: UUID, uid: UUID) -> SurveySchedule:
    p = await db.get(SurveySchedule, pid, with_for_update=True)
    if not p or uid not in (p.author_id, p.recipient_id):
        raise AppError(404, "NOT_FOUND")
    return p


async def create_wave(
    db: AsyncSession,
    p: SurveySchedule,
    key: str,
    due: datetime,
    now: datetime,
    cipher: PayloadCipher,
    base: str,
    occurrence: UUID | None = None,
) -> SurveyWave:
    old = await db.scalar(
        select(SurveyWave).where(SurveyWave.schedule_id == p.id, SurveyWave.event_key == key)
    )
    if old:
        return old
    body = command(p)
    v = await db.get(FormVersion, p.form_version_id)
    assert v is not None
    selected = {p.author_id, p.recipient_id, *body.reader_ids}
    users = (
        await db.scalars(
            select(User).where(User.id.in_(selected)).execution_options(populate_existing=True)
        )
    ).all()
    window = (
        timedelta(hours=body.schedule.window_hours)
        if body.schedule
        else timedelta(days=body.ttl_days)
    )
    reason = None
    if p.owner_paused or p.recipient_paused or (p.blocked_through and due <= p.blocked_through):
        reason = "paused"
    elif due < p.created_at:
        reason = "before_creation"
    elif due + window <= now:
        reason = "expired"
    elif len(users) != len(selected) or any(not u.is_active or u.paused for u in users):
        reason = "audience_unavailable"
    elif v.status != "published" or not await source_effective(db, p):
        reason = "source_unavailable"
    w = SurveyWave(
        id=uuid4(),
        schedule_id=p.id,
        event_key=key,
        due_at=due,
        occurrence_id=occurrence,
        status="skipped" if reason else "created",
        reason=reason,
    )
    if reason is None:
        invited = await invite(
            db,
            p.author_id,
            v.form_id,
            InvitationCreate(
                recipient_user_id=p.recipient_id,
                reader_ids=body.reader_ids,
                ttl_days=body.ttl_days,
                retention_days=body.retention_days,
                deliver=body.deliver,
            ),
            now,
            base,
            cipher,
            version_id=v.id,
        )
        invitation = await db.get(Invitation, invited.id)
        assert invitation is not None
        invitation.expires_at = due + window
        w.invitation_id = invited.id
    db.add(w)
    await db.flush()
    return w


async def generate_plan(
    db: AsyncSession,
    p: SurveySchedule,
    now: datetime,
    cipher: PayloadCipher,
    base: str,
    day_limit: int = 31,
) -> None:
    body = command(p)
    if body.schedule:
        from zoneinfo import ZoneInfo

        today = now.astimezone(ZoneInfo(body.schedule.timezone)).date()
        assert p.watermark is not None
        end = min(today, p.watermark + timedelta(days=day_limit - 1))
        for day in slot_days(body.schedule, p.watermark, end):
            due = local_slot(day, body.schedule.hour, body.schedule.minute, body.schedule.timezone)
            if due > now:
                p.watermark = day
                return
            await create_wave(db, p, "day:" + day.isoformat(), due, now, cipher, base)
        if end >= p.watermark:
            p.watermark = end + timedelta(days=1)
    else:
        events = (
            await db.scalars(
                select(RitualNotice)
                .where(
                    RitualNotice.assignment_id == p.ritual_assignment_id,
                    RitualNotice.user_id == p.recipient_id,
                    RitualNotice.kind == "approved",
                    RitualNotice.created_at >= p.created_at,
                    RitualNotice.created_at <= now,
                    RitualNotice.occurrence_id.is_not(None),
                    ~exists(
                        select(SurveyWave.id).where(
                            SurveyWave.schedule_id == p.id,
                            SurveyWave.occurrence_id == RitualNotice.occurrence_id,
                        )
                    ),
                )
                .order_by(RitualNotice.created_at, RitualNotice.id)
                .limit(100)
            )
        ).all()
        for n in events:
            if n.occurrence_id:
                await create_wave(
                    db,
                    p,
                    "occurrence:" + str(n.occurrence_id),
                    n.created_at,
                    now,
                    cipher,
                    base,
                    n.occurrence_id,
                )
    p.checked_at = now


async def generate(
    db: AsyncSession,
    now: datetime,
    cipher: PayloadCipher,
    base: str,
    limit: int = 50,
    day_limit: int = 31,
) -> None:
    rows = (
        await db.scalars(
            select(SurveySchedule)
            .order_by(SurveySchedule.checked_at.nullsfirst(), SurveySchedule.id)
            .with_for_update(skip_locked=True)
            .limit(limit)
        )
    ).all()
    for p in rows:
        await generate_plan(db, p, now, cipher, base, day_limit)
        p.checked_at = now
