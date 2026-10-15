from uuid import UUID, uuid4

from fastapi import APIRouter, Request
from sqlalchemy import select

from vowen.core.errors import AppError
from vowen.modules.auth.router import DB, Member
from vowen.modules.forms.service import active
from vowen.modules.identity.models import User
from vowen.modules.relations.router import cipher_for
from vowen.modules.rewards import service
from vowen.modules.rewards.models import RewardDefinition, RewardGrant, RewardNotice, RewardVersion
from vowen.modules.rewards.schemas import (
    GrantCommand,
    GrantTransitionCommand,
    GrantView,
    RewardContent,
    RewardEdit,
    RewardNoticeView,
    RewardView,
)
from vowen.modules.rituals.service import scoped

router = APIRouter(prefix="/api/v1")


@router.post("/rewards", response_model=RewardView)
async def create(body: RewardContent, principal: Member, db: DB, request: Request) -> RewardView:
    await active(db, principal.user_id)
    r = RewardDefinition(id=uuid4(), author_id=principal.user_id, revision=1)
    db.add(r)
    await db.flush()
    return await service.new_version(db, r, body, cipher_for(request))


@router.get("/rewards", response_model=list[RewardView])
async def catalogue(principal: Member, db: DB, request: Request) -> list[RewardView]:
    rows = (
        await db.scalars(
            select(RewardDefinition)
            .where(RewardDefinition.author_id == principal.user_id)
            .order_by(RewardDefinition.id)
        )
    ).all()
    result = []
    for r in rows:
        v = await db.get(RewardVersion, r.current_version_id)
        assert v is not None
        result.append(
            RewardView(
                id=r.id,
                version_id=v.id,
                revision=r.revision,
                **service.opened(v, cipher_for(request)),
            )
        )
    return result


@router.post("/rewards/{rid}/versions", response_model=RewardView)
async def version(
    rid: UUID, body: RewardEdit, principal: Member, db: DB, request: Request
) -> RewardView:
    await active(db, principal.user_id)
    r = await db.get(RewardDefinition, rid, with_for_update=True)
    if r is None or r.author_id != principal.user_id:
        raise AppError(404, "NOT_FOUND")
    if r.revision != body.expected_version:
        raise AppError(409, "VERSION_CONFLICT")
    r.revision += 1
    return await service.new_version(db, r, body, cipher_for(request))


@router.post("/reward-grants", response_model=GrantView)
async def grant(body: GrantCommand, principal: Member, db: DB, request: Request) -> GrantView:
    await db.get(User, principal.user_id, with_for_update=True)
    previous = await db.scalar(
        select(RewardGrant).where(
            RewardGrant.issuer_id == principal.user_id,
            RewardGrant.idempotency_key == body.idempotency_key,
        )
    )
    if previous:
        if (
            previous.recipient_id != body.recipient_id
            or previous.reward_version_id != body.reward_version_id
        ):
            raise AppError(409, "IDEMPOTENCY_CONFLICT")
        return await service.grant_view(db, previous, cipher_for(request))
    await service.owned_version(db, body.reward_version_id, principal.user_id)
    if not await scoped(
        db, principal.user_id, body.recipient_id, "rewards.grant", {principal.user_id}
    ):
        raise AppError(403, "ACCESS_DENIED")
    g = RewardGrant(
        id=uuid4(),
        reward_version_id=body.reward_version_id,
        recipient_id=body.recipient_id,
        issuer_id=principal.user_id,
        idempotency_key=body.idempotency_key,
        revision=1,
        status="offered",
        created_at=request.app.state.clock.now(),
    )
    db.add(g)
    await db.flush()
    await service.record(db, g, principal.user_id, g.created_at)
    await db.flush()
    return await service.grant_view(db, g, cipher_for(request))


@router.get("/reward-grants", response_model=list[GrantView])
async def grants(principal: Member, db: DB, request: Request) -> list[GrantView]:
    rows = (
        await db.scalars(
            select(RewardGrant)
            .where(
                (RewardGrant.recipient_id == principal.user_id)
                | (RewardGrant.issuer_id == principal.user_id)
            )
            .order_by(RewardGrant.created_at, RewardGrant.id)
        )
    ).all()
    return [await service.grant_view(db, g, cipher_for(request)) for g in rows]


@router.post("/reward-grants/{gid}/transitions", response_model=GrantView)
async def transition(
    gid: UUID, body: GrantTransitionCommand, principal: Member, db: DB, request: Request
) -> GrantView:
    g = await db.get(RewardGrant, gid, with_for_update=True)
    if g is None or principal.user_id not in (g.recipient_id, g.issuer_id):
        raise AppError(404, "NOT_FOUND")
    recipient = body.action in ("accept", "decline")
    if (g.recipient_id if recipient else g.issuer_id) != principal.user_id:
        raise AppError(403, "ACCESS_DENIED")
    if not recipient and not await scoped(
        db, g.issuer_id, g.recipient_id, "rewards.grant", {g.issuer_id}
    ):
        raise AppError(403, "ACCESS_DENIED")
    if body.expected_version != g.revision:
        raise AppError(409, "VERSION_CONFLICT")
    allowed = {
        "accept": {"offered"},
        "decline": {"offered"},
        "deliver": {"accepted"},
        "cancel": {"offered", "accepted"},
    }
    if g.status not in allowed[body.action]:
        raise AppError(409, "CONFLICT")
    g.status = {
        "accept": "accepted",
        "decline": "declined",
        "deliver": "delivered",
        "cancel": "cancelled",
    }[body.action]
    g.revision += 1
    await service.record(db, g, principal.user_id, request.app.state.clock.now())
    await db.flush()
    return await service.grant_view(db, g, cipher_for(request))


@router.get("/reward-notices", response_model=list[RewardNoticeView])
async def notices(principal: Member, db: DB) -> list[RewardNoticeView]:
    from vowen.modules.notifications.preferences import channel

    if not await channel(db, principal.user_id, "in_app"):
        return []
    rows = (
        await db.scalars(
            select(RewardNotice)
            .where(RewardNotice.user_id == principal.user_id)
            .order_by(RewardNotice.created_at.desc())
            .limit(100)
        )
    ).all()
    return [RewardNoticeView(id=n.id, grant_id=n.grant_id, created_at=n.created_at) for n in rows]
