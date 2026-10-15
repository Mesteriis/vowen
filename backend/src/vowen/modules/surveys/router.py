from uuid import UUID, uuid4

from fastapi import APIRouter, Request
from sqlalchemy import select

from vowen.core.errors import AppError
from vowen.modules.auth.router import DB, Member
from vowen.modules.forms.models import FormVersion
from vowen.modules.forms.service import active, form_owned
from vowen.modules.identity.models import User
from vowen.modules.relations.models import Relation
from vowen.modules.relations.router import cipher_for
from vowen.modules.relations.schemas import ExpectedVersion
from vowen.modules.rituals.models import RitualAssignment
from vowen.modules.rituals.service import effective
from vowen.modules.surveys import service as s
from vowen.modules.surveys.models import SurveySchedule, SurveyWave
from vowen.modules.surveys.schemas import SendWave, SurveyCreate, SurveyView, WaveView

router = APIRouter(prefix="/api/v1/survey-schedules")


@router.get("", response_model=list[SurveyView])
async def listing(principal: Member, db: DB) -> list[SurveyView]:
    rows = (
        await db.scalars(
            select(SurveySchedule)
            .where(
                (SurveySchedule.author_id == principal.user_id)
                | (SurveySchedule.recipient_id == principal.user_id)
            )
            .order_by(SurveySchedule.id)
        )
    ).all()
    return [await s.view(db, p) for p in rows]


@router.post("", response_model=SurveyView)
async def create(body: SurveyCreate, principal: Member, db: DB, request: Request) -> SurveyView:
    await active(db, principal.user_id)
    v = await db.get(FormVersion, body.form_version_id)
    if not v:
        raise AppError(404, "NOT_FOUND")
    await form_owned(db, v.form_id, principal.user_id)
    if v.status != "published":
        raise AppError(409, "PUBLISH_REQUIRED")
    config = body.model_dump(mode="json", exclude={"idempotency_key"})
    old = await db.scalar(
        select(SurveySchedule).where(
            SurveySchedule.author_id == principal.user_id,
            SurveySchedule.idempotency_key == body.idempotency_key,
        )
    )
    if old:
        if old.config != config:
            raise AppError(409, "IDEMPOTENCY_CONFLICT")
        return await s.view(db, old)
    selected = {principal.user_id, body.recipient_id, *body.reader_ids}
    users = (await db.scalars(select(User).where(User.id.in_(selected)))).all()
    if len(users) != len(selected) or any(not u.is_active or u.paused for u in users):
        raise AppError(422, "INVALID_AUDIENCE")
    source_revision = authority_revision = None
    if body.ritual_assignment_id:
        a = await db.get(RitualAssignment, body.ritual_assignment_id)
        if (
            not a
            or a.issuer_id != principal.user_id
            or a.recipient_id != body.recipient_id
            or not await effective(db, a)
        ):
            raise AppError(403, "ACCESS_DENIED")
        r = await db.scalar(
            select(Relation).where(
                Relation.dominant_user_id == principal.user_id,
                Relation.submissive_user_id == body.recipient_id,
                Relation.status == "active",
            )
        )
        assert r is not None
        source_revision, authority_revision = a.revision, r.version
    p = SurveySchedule(
        id=uuid4(),
        author_id=principal.user_id,
        recipient_id=body.recipient_id,
        form_version_id=v.id,
        idempotency_key=body.idempotency_key,
        config=config,
        ritual_assignment_id=body.ritual_assignment_id,
        source_revision=source_revision,
        authority_revision=authority_revision,
        created_at=request.app.state.clock.now(),
        watermark=body.schedule.start_date if body.schedule else None,
        revision=1,
        owner_paused=False,
        recipient_paused=False,
    )
    db.add(p)
    await db.flush()
    await s.generate_plan(
        db,
        p,
        request.app.state.clock.now(),
        cipher_for(request),
        request.app.state.settings.public_base_url,
    )
    return await s.view(db, p)


@router.get("/{pid}/waves", response_model=list[WaveView])
async def waves(pid: UUID, principal: Member, db: DB) -> list[WaveView]:
    await s.loaded(db, pid, principal.user_id)
    rows = (
        await db.scalars(
            select(SurveyWave)
            .where(SurveyWave.schedule_id == pid)
            .order_by(SurveyWave.due_at, SurveyWave.id)
        )
    ).all()
    return [s.wave_view(w) for w in rows]


@router.post("/{pid}/send-now", response_model=WaveView)
async def send_now(
    pid: UUID, body: SendWave, principal: Member, db: DB, request: Request
) -> WaveView:
    p = await s.loaded(db, pid, principal.user_id)
    if p.author_id != principal.user_id:
        raise AppError(403, "ACCESS_DENIED")
    if p.revision != body.expected_version:
        raise AppError(409, "VERSION_CONFLICT")
    now = request.app.state.clock.now()
    return s.wave_view(
        await s.create_wave(
            db,
            p,
            "manual:" + str(body.idempotency_key),
            now,
            now,
            cipher_for(request),
            request.app.state.settings.public_base_url,
        )
    )


@router.post("/{pid}/{action}", response_model=SurveyView)
async def transition(
    pid: UUID, action: str, body: ExpectedVersion, principal: Member, db: DB, request: Request
) -> SurveyView:
    if action not in ("pause", "resume"):
        raise AppError(404, "NOT_FOUND")
    p = await s.loaded(db, pid, principal.user_id)
    if p.revision != body.expected_version:
        raise AppError(409, "VERSION_CONFLICT")
    field = "owner_paused" if p.author_id == principal.user_id else "recipient_paused"
    value = action == "pause"
    if getattr(p, field) == value:
        raise AppError(409, "CONFLICT")
    if not value:
        await active(db, principal.user_id)
    setattr(p, field, value)
    p.revision += 1
    p.blocked_through = request.app.state.clock.now()
    return await s.view(db, p)
