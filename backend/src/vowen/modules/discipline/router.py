from uuid import UUID

from fastapi import APIRouter, Request
from sqlalchemy import select

from vowen.core.errors import AppError
from vowen.modules.auth.router import DB, Member
from vowen.modules.discipline import dictionaries
from vowen.modules.discipline import service as s
from vowen.modules.discipline.models import DisciplineRecord, DisciplineReviewer
from vowen.modules.discipline.schemas import (
    DisciplineContent,
    DisciplineCreate,
    DisciplineDecision,
    DisciplineDictionaryEntry,
    DisciplineEdit,
    DisciplineView,
)
from vowen.modules.forms.service import active
from vowen.modules.relations.router import cipher_for

router = APIRouter(prefix="/api/v1/discipline-records")


@router.get("/dictionaries/{relation_id}/{kind}", response_model=list[str])
async def dictionary_values(
    relation_id: UUID, kind: dictionaries.Kind, principal: Member, db: DB, request: Request
) -> list[str]:
    await dictionaries.relationship(db, relation_id, principal.user_id)
    return await dictionaries.values(db, relation_id, kind, cipher_for(request))


@router.post("/dictionaries/{relation_id}/{kind}", response_model=list[str])
async def dictionary_add(
    relation_id: UUID,
    kind: dictionaries.Kind,
    body: DisciplineDictionaryEntry,
    principal: Member,
    db: DB,
    request: Request,
) -> list[str]:
    await dictionaries.relationship(db, relation_id, principal.user_id, write=True)
    return await dictionaries.add(db, relation_id, kind, body.name, cipher_for(request))


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
    return await s.create_record(
        db, principal.user_id, body, cipher_for(request), request.app.state.clock.now()
    )


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
    if body.action in ("start", "complete") and not recipient:
        raise AppError(403, "ACCESS_DENIED")
    if body.action == "confirm" and (
        principal.user_id not in await s.reviewers(db, r)
        or not await s.permitted(db, principal.user_id, r.recipient_id, "discipline.review")
    ):
        raise AppError(403, "ACCESS_DENIED")
    if body.action == "cancel" and principal.user_id != r.author_id:
        raise AppError(403, "ACCESS_DENIED")
    allowed = {
        "start": ({"planned", "proposed", "accepted"}, "in_progress"),
        "complete": ({"in_progress"}, "completed"),
        "confirm": ({"completed"}, "confirmed"),
        "cancel": (
            {"planned", "proposed", "accepted", "in_progress", "completed", "disputed"},
            "cancelled",
        ),
    }
    sources, target = allowed[body.action]
    if r.status not in sources:
        raise AppError(409, "CONFLICT")
    if body.action != "cancel":
        await active(db, principal.user_id)
        if not await s.permitted(db, r.author_id, r.recipient_id, "discipline.propose"):
            raise AppError(403, "ACCESS_DENIED")
    r.status = target
    r.revision += 1
    await s.event(
        db, r, principal.user_id, body.comment, cipher_for(request), request.app.state.clock.now()
    )
    return await s.view(db, r, cipher_for(request))
