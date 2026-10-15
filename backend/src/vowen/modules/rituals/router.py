import hashlib
from datetime import timedelta
from typing import Literal
from uuid import UUID, uuid4
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Request
from sqlalchemy import func, select

from vowen.core.errors import AppError
from vowen.modules.auth.router import DB, Member
from vowen.modules.forms.service import active
from vowen.modules.identity.models import User
from vowen.modules.relations.router import cipher_for
from vowen.modules.relations.schemas import ExpectedVersion
from vowen.modules.rituals import service as rituals
from vowen.modules.rituals.models import (
    Ritual,
    RitualAssignment,
    RitualNotice,
    RitualOccurrence,
    RitualReport,
    RitualReviewer,
    RitualSchedule,
    RitualVersion,
)
from vowen.modules.rituals.schemas import (
    OccurrenceView,
    ReportCommand,
    ReviewCommand,
    RitualAssign,
    RitualAssignmentView,
    RitualContent,
    RitualEdit,
    RitualNoticeView,
    RitualView,
    ScheduleEdit,
)
from vowen.modules.rituals.worker import generate_assignment

router = APIRouter(prefix="/api/v1")


@router.post("/rituals", response_model=RitualView)
async def create(body: RitualContent, principal: Member, db: DB, request: Request) -> RitualView:
    await active(db, principal.user_id)
    r = Ritual(id=uuid4(), author_id=principal.user_id)
    db.add(r)
    await db.flush()
    await rituals.new_version(db, r, body, cipher_for(request))
    return await rituals.view(db, r, cipher_for(request))


@router.get("/rituals", response_model=list[RitualView])
async def listing(principal: Member, db: DB, request: Request) -> list[RitualView]:
    rows = (
        await db.scalars(
            select(Ritual).where(Ritual.author_id == principal.user_id).order_by(Ritual.id)
        )
    ).all()
    return [await rituals.view(db, r, cipher_for(request)) for r in rows]


@router.get("/rituals/{rid}/versions", response_model=list[RitualView])
async def history(rid: UUID, principal: Member, db: DB, request: Request) -> list[RitualView]:
    r = await rituals.owned(db, rid, principal.user_id)
    versions = (
        await db.scalars(
            select(RitualVersion).where(RitualVersion.ritual_id == rid).order_by(RitualVersion.id)
        )
    ).all()
    return [
        RitualView(
            id=rid,
            version_id=v.id,
            revision=r.revision,
            status=v.status,
            **rituals.opened(v, cipher_for(request)),
        )
        for v in versions
    ]


@router.patch("/rituals/{rid}", response_model=RitualView)
async def edit(
    rid: UUID, body: RitualEdit, principal: Member, db: DB, request: Request
) -> RitualView:
    await active(db, principal.user_id)
    r = await rituals.owned(db, rid, principal.user_id, body.expected_version)
    v = await db.get(RitualVersion, r.current_version_id)
    assert v is not None
    if v.status != "draft":
        raise AppError(409, "IMMUTABLE_VERSION")
    rituals.seal(v, {"title": body.title, "description": body.description}, cipher_for(request))
    r.revision += 1
    return await rituals.view(db, r, cipher_for(request))


@router.post("/rituals/{rid}/versions", response_model=RitualView)
async def version(
    rid: UUID, body: RitualEdit, principal: Member, db: DB, request: Request
) -> RitualView:
    await active(db, principal.user_id)
    r = await rituals.owned(db, rid, principal.user_id, body.expected_version)
    v = await db.get(RitualVersion, r.current_version_id)
    assert v is not None
    if v.status == "draft":
        raise AppError(409, "UNPUBLISHED_VERSION")
    await rituals.new_version(db, r, body, cipher_for(request))
    r.revision += 1
    return await rituals.view(db, r, cipher_for(request))


@router.post("/rituals/{rid}/assignments", response_model=RitualAssignmentView)
async def assign(
    rid: UUID, body: RitualAssign, principal: Member, db: DB, request: Request
) -> RitualAssignmentView:
    # Lock issuer before checking a cross-template idempotency key.
    await db.get(User, principal.user_id, with_for_update=True)
    r = await rituals.owned(db, rid, principal.user_id)
    digest = hashlib.sha256((str(rid) + body.model_dump_json()).encode()).digest()
    previous = await db.scalar(
        select(RitualAssignment).where(
            RitualAssignment.issuer_id == principal.user_id,
            RitualAssignment.idempotency_key == body.idempotency_key,
        )
    )
    if previous is not None:
        if previous.request_hash != digest:
            raise AppError(409, "IDEMPOTENCY_CONFLICT")
        # A retry cannot bypass current authority even though it has no new effects.
        if not await rituals.effective(db, previous):
            raise AppError(403, "ACCESS_DENIED")
        return await rituals.assignment_view(db, previous, cipher_for(request))
    v = await db.get(RitualVersion, r.current_version_id)
    assert v is not None
    if v.status != "published":
        raise AppError(409, "UNPUBLISHED_VERSION")
    if not await rituals.scoped(
        db, principal.user_id, body.recipient_id, "rituals.assign", {principal.user_id}
    ):
        raise AppError(403, "ACCESS_DENIED")
    for uid in body.reviewer_ids:
        if not await rituals.scoped(db, uid, body.recipient_id, "rituals.review", {uid}):
            raise AppError(403, "ACCESS_DENIED")
    now = request.app.state.clock.now()
    if body.schedule.start_date < now.astimezone(ZoneInfo(body.schedule.timezone)).date():
        raise AppError(422, "PAST_START_DATE")
    a = RitualAssignment(
        id=uuid4(),
        ritual_version_id=v.id,
        recipient_id=body.recipient_id,
        issuer_id=principal.user_id,
        approval_required=body.approval_required,
        watermark=body.schedule.start_date,
        idempotency_key=body.idempotency_key,
        request_hash=digest,
    )
    db.add(a)
    await db.flush()
    s = RitualSchedule(
        id=uuid4(),
        assignment_id=a.id,
        starts_on=body.schedule.start_date,
        spec=body.schedule.model_dump(mode="json"),
    )
    db.add(s)
    await db.flush()
    a.current_schedule_id = s.id
    db.add_all([RitualReviewer(assignment_id=a.id, user_id=uid) for uid in body.reviewer_ids])
    await db.flush()
    await rituals.notice(db, a, [a.recipient_id], "assigned", now)
    await generate_assignment(db, a, now, 31)
    return await rituals.assignment_view(db, a, cipher_for(request))


@router.post("/rituals/{rid}/{action}", response_model=RitualView)
async def template_action(
    rid: UUID,
    action: Literal["publish", "archive"],
    body: ExpectedVersion,
    principal: Member,
    db: DB,
    request: Request,
) -> RitualView:
    r = await rituals.owned(db, rid, principal.user_id, body.expected_version)
    v = await db.get(RitualVersion, r.current_version_id)
    assert v is not None
    if action == "publish":
        await active(db, principal.user_id)
        if v.status != "draft":
            raise AppError(409, "CONFLICT")
        v.status = "published"
    else:
        if v.status == "archived":
            raise AppError(409, "CONFLICT")
        v.status = "archived"
    r.revision += 1
    return await rituals.view(db, r, cipher_for(request))


async def assigned(db: DB, uid: UUID) -> list[RitualAssignment]:
    return list(
        await db.scalars(
            select(RitualAssignment)
            .where(
                (RitualAssignment.recipient_id == uid)
                | RitualAssignment.id.in_(
                    select(RitualReviewer.assignment_id).where(RitualReviewer.user_id == uid)
                )
            )
            .order_by(RitualAssignment.id)
        )
    )


@router.get("/ritual-assignments", response_model=list[RitualAssignmentView])
async def assignments(principal: Member, db: DB, request: Request) -> list[RitualAssignmentView]:
    return [
        await rituals.assignment_view(db, a, cipher_for(request))
        for a in await assigned(db, principal.user_id)
        if await rituals.visible(db, a, principal.user_id)
    ]


@router.get("/ritual-occurrences", response_model=list[OccurrenceView])
async def occurrences(principal: Member, db: DB, request: Request) -> list[OccurrenceView]:
    result = []
    for a in await assigned(db, principal.user_id):
        if not await rituals.visible(db, a, principal.user_id):
            continue
        rows = (
            await db.scalars(
                select(RitualOccurrence)
                .where(RitualOccurrence.assignment_id == a.id)
                .order_by(RitualOccurrence.due_at.desc(), RitualOccurrence.id)
            )
        ).all()
        result.extend(
            [
                await rituals.occurrence_view(
                    db, o, a, principal.user_id, request.app.state.clock.now(), cipher_for(request)
                )
                for o in rows
            ]
        )
    return result


@router.post("/ritual-occurrences/{oid}/report", response_model=OccurrenceView)
async def report(
    oid: UUID, body: ReportCommand, principal: Member, db: DB, request: Request
) -> OccurrenceView:
    a, o = await rituals.locked(db, oid)
    if a.recipient_id != principal.user_id:
        raise AppError(403, "ACCESS_DENIED")
    previous = await db.scalar(
        select(RitualReport).where(
            RitualReport.occurrence_id == oid, RitualReport.idempotency_key == body.idempotency_key
        )
    )
    if previous is not None:
        if rituals.opened(previous, cipher_for(request))["text"] != body.text:
            raise AppError(409, "IDEMPOTENCY_CONFLICT")
        return await rituals.occurrence_view(
            db, o, a, principal.user_id, request.app.state.clock.now(), cipher_for(request)
        )
    if o.revision != body.expected_version:
        raise AppError(409, "VERSION_CONFLICT")
    now = request.app.state.clock.now()
    if not await rituals.effective(db, a):
        raise AppError(403, "ACCESS_DENIED")
    if o.status not in ("scheduled", "needs_changes") or not o.due_at <= now < o.expires_at:
        raise AppError(409, "OCCURRENCE_CLOSED")
    attempt = (
        await db.scalar(
            select(func.count()).select_from(RitualReport).where(RitualReport.occurrence_id == oid)
        )
    ) or 0
    row = RitualReport(
        attempt=attempt + 1,
        id=uuid4(),
        occurrence_id=o.id,
        idempotency_key=body.idempotency_key,
        submitted_at=now,
    )
    rituals.seal(row, {"text": body.text}, cipher_for(request))
    db.add(row)
    o.status = "submitted" if a.approval_required else "approved"
    o.revision += 1
    await db.flush()
    targets = await rituals.reviewers(db, a) if a.approval_required else [a.recipient_id]
    await rituals.notice(db, a, targets, o.status, now, o, event=f"report:{row.id}")
    return await rituals.occurrence_view(db, o, a, principal.user_id, now, cipher_for(request))


@router.post("/ritual-occurrences/{oid}/review", response_model=OccurrenceView)
async def review(
    oid: UUID, body: ReviewCommand, principal: Member, db: DB, request: Request
) -> OccurrenceView:
    a, o = await rituals.locked(db, oid)
    if not await rituals.can_review(db, a, principal.user_id) or not await rituals.effective(db, a):
        raise AppError(403, "ACCESS_DENIED")
    if o.revision != body.expected_version:
        raise AppError(409, "VERSION_CONFLICT")
    if o.status != "submitted":
        raise AppError(409, "CONFLICT")
    row = await db.scalar(
        select(RitualReport)
        .where(RitualReport.occurrence_id == oid, RitualReport.reviewed_at.is_(None))
        .order_by(RitualReport.submitted_at.desc(), RitualReport.id)
        .limit(1)
    )
    assert row is not None
    payload = rituals.opened(row, cipher_for(request))
    payload["comment"] = body.comment
    rituals.seal(row, payload, cipher_for(request))
    row.decision, row.reviewer_id, row.reviewed_at = (
        body.decision,
        principal.user_id,
        request.app.state.clock.now(),
    )
    o.status = body.decision
    o.revision += 1
    await rituals.notice(
        db,
        a,
        [a.recipient_id],
        body.decision,
        request.app.state.clock.now(),
        o,
        event=f"review:{row.id}",
    )
    return await rituals.occurrence_view(
        db, o, a, principal.user_id, request.app.state.clock.now(), cipher_for(request)
    )


@router.post("/ritual-occurrences/{oid}/skip", response_model=OccurrenceView)
async def skip(
    oid: UUID, body: ExpectedVersion, principal: Member, db: DB, request: Request
) -> OccurrenceView:
    a, o = await rituals.locked(db, oid)
    if a.recipient_id != principal.user_id:
        raise AppError(403, "ACCESS_DENIED")
    if o.revision != body.expected_version or o.status not in ("scheduled", "needs_changes"):
        raise AppError(409, "CONFLICT")
    o.status = "skipped"
    o.revision += 1
    return await rituals.occurrence_view(
        db, o, a, principal.user_id, request.app.state.clock.now(), cipher_for(request)
    )


@router.post("/ritual-assignments/{aid}/{action}", response_model=RitualAssignmentView)
async def assignment_action(
    aid: UUID,
    action: Literal["pause", "resume", "revoke"],
    body: ExpectedVersion,
    principal: Member,
    db: DB,
    request: Request,
) -> RitualAssignmentView:
    a = await db.get(RitualAssignment, aid, with_for_update=True)
    if a is None:
        raise AppError(404, "NOT_FOUND")
    recipient = a.recipient_id == principal.user_id
    if not recipient and (a.issuer_id != principal.user_id or not await rituals.effective(db, a)):
        raise AppError(403, "ACCESS_DENIED")
    if a.revision != body.expected_version:
        raise AppError(409, "VERSION_CONFLICT")
    if a.status == "revoked" or (action == "resume" and (a.status != "paused" or not recipient)):
        raise AppError(409, "CONFLICT")
    if action == "resume":
        if not await rituals.scoped(
            db, a.issuer_id, a.recipient_id, "rituals.assign", {a.issuer_id}
        ):
            raise AppError(403, "ACCESS_DENIED")
        a.status = "active"
    else:
        a.status = "paused" if action == "pause" else "revoked"
        rows = (
            await db.scalars(
                select(RitualOccurrence)
                .where(
                    RitualOccurrence.assignment_id == aid,
                    RitualOccurrence.status.in_(["scheduled", "needs_changes"]),
                )
                .with_for_update()
            )
        ).all()
        for o in rows:
            o.status = "cancelled"
            o.revision += 1
    a.revision += 1
    await generate_assignment(db, a, request.app.state.clock.now(), 31)
    return await rituals.assignment_view(db, a, cipher_for(request))


@router.put("/ritual-assignments/{aid}/schedule", response_model=RitualAssignmentView)
async def schedule_edit(
    aid: UUID, body: ScheduleEdit, principal: Member, db: DB, request: Request
) -> RitualAssignmentView:
    a = await db.get(RitualAssignment, aid, with_for_update=True)
    if a is None or a.issuer_id != principal.user_id:
        raise AppError(404, "NOT_FOUND")
    if not await rituals.effective(db, a):
        raise AppError(403, "ACCESS_DENIED")
    if a.revision != body.expected_version:
        raise AppError(409, "VERSION_CONFLICT")
    old = await db.get(RitualSchedule, a.current_schedule_id)
    assert old is not None
    now = request.app.state.clock.now()
    if body.schedule.timezone != str(old.spec["timezone"]):
        raise AppError(422, "TIMEZONE_REQUIRES_NEW_ASSIGNMENT")
    minimum = max(
        now.astimezone(ZoneInfo(str(old.spec["timezone"]))).date(),
        now.astimezone(ZoneInfo(body.schedule.timezone)).date(),
    ) + timedelta(days=1)
    if body.schedule.start_date < minimum:
        raise AppError(422, "FUTURE_START_REQUIRED")
    # A pending future schedule cannot be edited again until it has started.
    if old.starts_on > minimum - timedelta(days=1):
        raise AppError(409, "PENDING_SCHEDULE")
    old.ends_on = body.schedule.start_date - timedelta(days=1)
    s = RitualSchedule(
        id=uuid4(),
        assignment_id=aid,
        starts_on=body.schedule.start_date,
        spec=body.schedule.model_dump(mode="json"),
    )
    db.add(s)
    await db.flush()
    a.current_schedule_id = s.id
    a.revision += 1
    return await rituals.assignment_view(db, a, cipher_for(request))


@router.get("/ritual-notices", response_model=list[RitualNoticeView])
async def notices(principal: Member, db: DB) -> list[RitualNoticeView]:
    rows = (
        await db.scalars(
            select(RitualNotice)
            .where(RitualNotice.user_id == principal.user_id)
            .order_by(RitualNotice.created_at.desc(), RitualNotice.id)
            .limit(100)
        )
    ).all()
    result = []
    for n in rows:
        a = await db.get(RitualAssignment, n.assignment_id)
        assert a is not None
        if await rituals.visible(db, a, principal.user_id):
            result.append(
                RitualNoticeView(
                    id=n.id,
                    occurrence_id=n.occurrence_id,
                    assignment_id=a.id,
                    kind=n.kind,
                    created_at=n.created_at,
                )
            )
    return result
