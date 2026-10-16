from uuid import UUID, uuid4

from fastapi import APIRouter, Request
from sqlalchemy import select

from vowen.core.errors import AppError
from vowen.modules.auth.router import DB, Member
from vowen.modules.relations.router import cipher_for
from vowen.modules.rewards import economy as e
from vowen.modules.rewards import service
from vowen.modules.rewards.economy_models import CurrencyEntry, ShopListing
from vowen.modules.rewards.economy_schemas import (
    CreditCommand,
    ListingCommand,
    ListingEdit,
    ListingView,
    PurchaseCommand,
    WalletView,
)
from vowen.modules.rewards.models import RewardGrant
from vowen.modules.rewards.schemas import GrantView

router = APIRouter(prefix="/api/v1")


@router.get("/relations/{rid}/wallet", response_model=WalletView)
async def wallet(rid: UUID, principal: Member, db: DB, request: Request) -> WalletView:
    await e.relation(db, rid, principal.user_id)
    return await e.wallet_view(db, rid, cipher_for(request))


@router.post("/relations/{rid}/wallet/credits", response_model=WalletView)
async def credit(
    rid: UUID, body: CreditCommand, principal: Member, db: DB, request: Request
) -> WalletView:
    r = await e.relation(db, rid, principal.user_id, write=True)
    if principal.user_id != r.dominant_user_id:
        raise AppError(403, "ACCESS_DENIED")
    await e.locked_wallet(db, rid)
    old = await db.scalar(
        select(CurrencyEntry).where(
            CurrencyEntry.relation_id == rid,
            CurrencyEntry.actor_id == principal.user_id,
            CurrencyEntry.idempotency_key == body.idempotency_key,
        )
    )
    if old:
        if (
            old.kind != "manual"
            or old.amount != body.amount
            or e.comment(old, cipher_for(request)) != body.comment
        ):
            raise AppError(409, "IDEMPOTENCY_CONFLICT")
    else:
        await e.append(
            db,
            rid,
            principal.user_id,
            body.amount,
            "manual",
            body.comment,
            request.app.state.clock.now(),
            cipher_for(request),
            key=body.idempotency_key,
        )
    return await e.wallet_view(db, rid, cipher_for(request))


@router.get("/relations/{rid}/shop", response_model=list[ListingView])
async def shop(rid: UUID, principal: Member, db: DB, request: Request) -> list[ListingView]:
    r = await e.relation(db, rid, principal.user_id)
    if principal.user_id != r.dominant_user_id:
        from vowen.modules.rituals.service import scoped

        if r.status != "active" or not await scoped(
            db, r.dominant_user_id, r.submissive_user_id, "rewards.grant", {r.dominant_user_id}
        ):
            return []
    rows = (
        await db.scalars(
            select(ShopListing).where(ShopListing.relation_id == rid).order_by(ShopListing.id)
        )
    ).all()
    return [
        await e.listing_view(db, s, cipher_for(request))
        for s in rows
        if s.active or r.dominant_user_id == principal.user_id
    ]


@router.post("/relations/{rid}/shop", response_model=ListingView)
async def create_listing(
    rid: UUID, body: ListingCommand, principal: Member, db: DB, request: Request
) -> ListingView:
    r = await e.relation(db, rid, principal.user_id, write=True)
    if r.dominant_user_id != principal.user_id:
        raise AppError(403, "ACCESS_DENIED")
    await service.owned_version(db, body.reward_version_id, principal.user_id)
    s = ShopListing(
        id=uuid4(), relation_id=rid, reward_version_id=body.reward_version_id, price=body.price
    )
    db.add(s)
    await db.flush()
    return await e.listing_view(db, s, cipher_for(request))


@router.patch("/shop/{sid}", response_model=ListingView)
async def edit_listing(
    sid: UUID, body: ListingEdit, principal: Member, db: DB, request: Request
) -> ListingView:
    s = await db.get(ShopListing, sid)
    if s is None:
        raise AppError(404, "NOT_FOUND")
    r = await e.relation(db, s.relation_id, principal.user_id, write=True)
    if r.dominant_user_id != principal.user_id:
        raise AppError(403, "ACCESS_DENIED")
    s = await db.get(ShopListing, sid, with_for_update=True, populate_existing=True)
    assert s is not None
    if s.revision != body.expected_version:
        raise AppError(409, "VERSION_CONFLICT")
    s.price, s.active = body.price, body.active
    s.revision += 1
    return await e.listing_view(db, s, cipher_for(request))


@router.post("/shop/{sid}/purchases", response_model=GrantView)
async def purchase(
    sid: UUID, body: PurchaseCommand, principal: Member, db: DB, request: Request
) -> GrantView:
    s = await db.get(ShopListing, sid)
    if s is None:
        raise AppError(404, "NOT_FOUND")
    r = await e.relation(db, s.relation_id, principal.user_id, write=True)
    if r.submissive_user_id != principal.user_id:
        raise AppError(403, "ACCESS_DENIED")
    s = await db.get(ShopListing, sid, with_for_update=True, populate_existing=True)
    assert s is not None
    await e.locked_wallet(db, r.id)
    old = await db.scalar(
        select(CurrencyEntry).where(
            CurrencyEntry.relation_id == r.id,
            CurrencyEntry.actor_id == principal.user_id,
            CurrencyEntry.idempotency_key == body.idempotency_key,
        )
    )
    if old:
        if old.kind != "purchase" or old.listing_id != sid:
            raise AppError(409, "IDEMPOTENCY_CONFLICT")
        g = await db.get(RewardGrant, old.grant_id)
        assert g is not None
        return await service.grant_view(db, g, cipher_for(request))
    if not s.active or s.revision != body.expected_version:
        raise AppError(409, "LISTING_CHANGED")
    if await e.balance(db, r.id) < s.price:
        raise AppError(409, "INSUFFICIENT_BALANCE")
    now = request.app.state.clock.now()
    g = RewardGrant(
        id=uuid4(),
        reward_version_id=s.reward_version_id,
        recipient_id=principal.user_id,
        issuer_id=r.dominant_user_id,
        idempotency_key=uuid4(),
        revision=1,
        status="accepted",
        created_at=now,
    )
    db.add(g)
    await db.flush()
    await e.append(
        db,
        r.id,
        principal.user_id,
        -s.price,
        "purchase",
        "",
        now,
        cipher_for(request),
        key=body.idempotency_key,
        grant_id=g.id,
        listing_id=sid,
    )
    await service.record(db, g, principal.user_id, now)
    return await service.grant_view(db, g, cipher_for(request))
