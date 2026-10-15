from uuid import UUID, uuid4

from fastapi import APIRouter, Request
from sqlalchemy import select

from vowen.core.errors import AppError
from vowen.modules.auth.router import DB, Member
from vowen.modules.discipline import service as s
from vowen.modules.discipline.models import DisciplineRecord, DisciplineReviewer
from vowen.modules.discipline.schemas import (
    DisciplineContent,
    DisciplineCreate,
    DisciplineDecision,
    DisciplineEdit,
    DisciplineView,
)
from vowen.modules.forms.service import active
from vowen.modules.relations.router import cipher_for

router = APIRouter(prefix="/api/v1/discipline-records")


@router.get("", response_model=list[DisciplineView])
async def listing(principal: Member, db: DB, request: Request) -> list[DisciplineView]:
    rows = (
        await db.scalars(
            select(DisciplineRecord)
            .where(
                (DisciplineRecord.author_id == principal.user_id)
                | (DisciplineRecord.recipient_id == principal.user_id)
                | DisciplineRecord.id.in_(
                    select(DisciplineReviewer.record_id).where(
                        DisciplineReviewer.user_id == principal.user_id
                    )
                )
            )
            .order_by(DisciplineRecord.id)
        )
    ).all()
    return [
        await s.view(db, r, cipher_for(request))
        for r in rows
        if await s.visible(db, r, principal.user_id)
    ]


@router.post("", response_model=DisciplineView)
async def create(
    body: DisciplineCreate, principal: Member, db: DB, request: Request
) -> DisciplineView:
    if principal.user_id == body.recipient_id or body.recipient_id in body.reviewer_ids:
        raise AppError(422, "INVALID_INPUT")
    await s.lock_authority(db, body.recipient_id, [principal.user_id, *body.reviewer_ids])
    if not await s.permitted(db, principal.user_id, body.recipient_id, "discipline.propose"):
        raise AppError(403, "ACCESS_DENIED")
    for uid in body.reviewer_ids:
        if not await s.permitted(db, uid, body.recipient_id, "discipline.review"):
            raise AppError(403, "ACCESS_DENIED")
    previous = await db.scalar(
        select(DisciplineRecord).where(
            DisciplineRecord.author_id == principal.user_id,
            DisciplineRecord.idempotency_key == body.idempotency_key,
        )
    )
    cipher = cipher_for(request)
    content = DisciplineContent.model_validate(
        body.model_dump(include=set(DisciplineContent.model_fields))
    )
    if previous is not None:
        previous_view = await s.view(db, previous, cipher)
        v = previous_view.versions
        initial = previous_view.history[0].version_id
        first = next(x for x in v if x.id == initial)
        if (
            previous.recipient_id != body.recipient_id
            or set(await s.reviewers(db, previous)) != set(body.reviewer_ids)
            or any(getattr(first, k) != getattr(content, k) for k in DisciplineContent.model_fields)
        ):
            raise AppError(409, "IDEMPOTENCY_CONFLICT")
        return await s.view(db, previous, cipher)
    r = DisciplineRecord(
        id=uuid4(),
        author_id=principal.user_id,
        recipient_id=body.recipient_id,
        idempotency_key=body.idempotency_key,
        revision=1,
        status="proposed",
    )
    db.add(r)
    await db.flush()
    db.add_all([DisciplineReviewer(record_id=r.id, user_id=uid) for uid in body.reviewer_ids])
    await s.version(db, r, content, cipher, request.app.state.clock.now())
    await s.event(db, r, principal.user_id, "", cipher, request.app.state.clock.now())
    return await s.view(db, r, cipher)


@router.get("/{rid}", response_model=DisciplineView)
async def detail(rid: UUID, principal: Member, db: DB, request: Request) -> DisciplineView:
    r = await s.locked(db, rid, principal.user_id)
    return await s.view(db, r, cipher_for(request))


@router.post("/{rid}/versions", response_model=DisciplineView)
async def revise(
    rid: UUID, body: DisciplineEdit, principal: Member, db: DB, request: Request
) -> DisciplineView:
    r = await s.locked(db, rid, principal.user_id)
    if r.author_id != principal.user_id:
        raise AppError(403, "ACCESS_DENIED")
    if r.revision != body.expected_version:
        raise AppError(409, "VERSION_CONFLICT")
    if r.status in ("confirmed", "declined", "cancelled"):
        raise AppError(409, "CONFLICT")
    if not await s.permitted(db, r.author_id, r.recipient_id, "discipline.propose"):
        raise AppError(403, "ACCESS_DENIED")
    cipher = cipher_for(request)
    await s.version(
        db,
        r,
        DisciplineContent.model_validate(body.model_dump(exclude={"expected_version"})),
        cipher,
        request.app.state.clock.now(),
    )
    r.revision += 1
    await s.event(db, r, principal.user_id, "", cipher, request.app.state.clock.now())
    return await s.view(db, r, cipher)


@router.post("/{rid}/transitions", response_model=DisciplineView)
async def transition(
    rid: UUID, body: DisciplineDecision, principal: Member, db: DB, request: Request
) -> DisciplineView:
    r = await s.locked(db, rid, principal.user_id)
    if r.revision != body.expected_version or r.current_version_id != body.version_id:
        raise AppError(409, "VERSION_CONFLICT")
    recipient = principal.user_id == r.recipient_id
    if body.action in ("accept", "start", "complete", "decline", "dispute") and not recipient:
        raise AppError(403, "ACCESS_DENIED")
    if body.action == "confirm" and (
        principal.user_id not in await s.reviewers(db, r)
        or not await s.permitted(db, principal.user_id, r.recipient_id, "discipline.review")
    ):
        raise AppError(403, "ACCESS_DENIED")
    allowed = {
        "accept": ({"proposed"}, "accepted"),
        "start": ({"accepted"}, "in_progress"),
        "complete": ({"in_progress"}, "completed"),
        "confirm": ({"completed"}, "confirmed"),
        "decline": ({"proposed"}, "declined"),
        "dispute": ({"proposed", "accepted", "in_progress", "completed"}, "disputed"),
        "cancel": ({"proposed", "accepted", "in_progress", "completed", "disputed"}, "cancelled"),
    }
    sources, target = allowed[body.action]
    if r.status not in sources:
        raise AppError(409, "CONFLICT")
    if body.action not in ("cancel", "decline", "dispute"):
        await active(db, principal.user_id)
        if not await s.permitted(db, r.author_id, r.recipient_id, "discipline.propose"):
            raise AppError(403, "ACCESS_DENIED")
    r.status = target
    r.revision += 1
    await s.event(
        db, r, principal.user_id, body.comment, cipher_for(request), request.app.state.clock.now()
    )
    return await s.view(db, r, cipher_for(request))
