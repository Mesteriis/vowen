from uuid import UUID, uuid4

from fastapi import APIRouter, Request
from sqlalchemy import select

from vowen.core.errors import AppError
from vowen.modules.auth.router import DB, Member
from vowen.modules.identity.models import User
from vowen.modules.relations.router import cipher_for
from vowen.modules.rewards import economy as e
from vowen.modules.rewards import service
from vowen.modules.rewards.economy_models import CurrencyEntry, ShopListing
from vowen.modules.rewards.economy_schemas import (
    AvailabilityCommand,
    CreditCommand,
    ListingCommand,
    ListingEdit,
    ListingView,
    PurchaseCommand,
    WalletView,
)
from vowen.modules.rewards.models import RewardVersion
from vowen.modules.rewards.schemas import GrantView

router = APIRouter(prefix="/api/v1")


@router.get("/shop/catalogue", response_model=list[ListingView])
async def catalogue(
    principal: Member, db: DB, request: Request, relation_id: UUID | None = None
) -> list[ListingView]:
    from vowen.modules.rewards.catalogue import listing_catalogue

    return await listing_catalogue(db, principal.user_id, cipher_for(request), relation_id)


@router.get("/relations/{rid}/wallet", response_model=WalletView)
async def wallet(rid: UUID, principal: Member, db: DB, request: Request) -> WalletView:
    await e.relation(db, rid, principal.user_id)
    return await e.wallet_view(db, rid, cipher_for(request))


@router.post("/relations/{rid}/wallet/credits", response_model=WalletView)
async def credit(
    rid: UUID, body: CreditCommand, principal: Member, db: DB, request: Request
) -> WalletView:
    from vowen.modules.rewards.permissions import shop_user

    await shop_user(db, principal.user_id, manage=True, write=True)
    r = await e.relation(db, rid, principal.user_id, write=True)
    await shop_user(db, principal.user_id, manage=True, write=True)
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
    from vowen.modules.rewards.permissions import shop_user

    actor = await shop_user(db, principal.user_id)
    if actor.shop_role != "dominant":
        from vowen.modules.rewards.catalogue import listing_catalogue

        if r.status != "active":
            return []
        return await listing_catalogue(db, principal.user_id, cipher_for(request), rid)
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
    from vowen.modules.rewards.permissions import shop_user

    await shop_user(db, principal.user_id, manage=True, write=True)
    r = await e.relation(db, rid, principal.user_id, write=True)
    await shop_user(db, principal.user_id, manage=True, write=True)
    if r.dominant_user_id != principal.user_id:
        raise AppError(403, "ACCESS_DENIED")
    await service.owned_version(db, body.reward_version_id, principal.user_id)
    await db.get(RewardVersion, body.reward_version_id, with_for_update=True)
    s = ShopListing(
        id=uuid4(),
        relation_id=rid,
        reward_version_id=body.reward_version_id,
        price=body.price,
    )
    db.add(s)
    await db.flush()
    return await e.listing_view(db, s, cipher_for(request))


@router.patch("/shop/{sid}", response_model=ListingView)
async def edit_listing(
    sid: UUID, body: ListingEdit, principal: Member, db: DB, request: Request
) -> ListingView:
    from vowen.modules.rewards.permissions import shop_user

    await shop_user(db, principal.user_id, manage=True, write=True)
    s = await db.get(ShopListing, sid)
    if s is None:
        raise AppError(404, "NOT_FOUND")
    r = await e.relation(db, s.relation_id, principal.user_id, write=True)
    await shop_user(db, principal.user_id, manage=True, write=True)
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
    from vowen.modules.rewards.orders import request_purchase

    return await request_purchase(
        db, sid, principal.user_id, body, request.app.state.clock.now(), cipher_for(request)
    )


@router.get("/shop/availability/{version_id}", response_model=list[ListingView])
async def availability(
    version_id: UUID, principal: Member, db: DB, request: Request
) -> list[ListingView]:
    await service.owned_version(db, version_id, principal.user_id)
    rows = (
        await db.scalars(
            select(ShopListing)
            .where(ShopListing.reward_version_id == version_id)
            .order_by(ShopListing.id)
        )
    ).all()
    for row in rows:
        if row.relation_id is None:
            continue
        r = await e.relation(db, row.relation_id, principal.user_id)
        if r.dominant_user_id != principal.user_id:
            raise AppError(403, "ACCESS_DENIED")
    return [await e.listing_view(db, row, cipher_for(request)) for row in rows]


@router.post("/shop/availability", response_model=list[ListingView])
async def set_availability(
    body: AvailabilityCommand, principal: Member, db: DB, request: Request
) -> list[ListingView]:
    from vowen.modules.rewards.permissions import shop_user

    await shop_user(db, principal.user_id, manage=True, write=True)
    await service.owned_version(db, body.reward_version_id, principal.user_id)
    rows = (
        await db.scalars(
            select(ShopListing).where(ShopListing.reward_version_id == body.reward_version_id)
        )
    ).all()
    if body.audience_all and not rows and not body.relation_ids:
        raise AppError(422, "RELATION_REQUIRED")
    relation_ids = set(body.relation_ids) | {
        row.relation_id for row in rows if row.relation_id is not None
    }
    parties: set[UUID] = set()
    for rid in sorted(relation_ids):
        r = await e.relation(db, rid, principal.user_id)
        if r.dominant_user_id != principal.user_id:
            raise AppError(403, "ACCESS_DENIED")
        parties.update((r.dominant_user_id, r.submissive_user_id))
    # Match all economy operations: globally ordered parties, relations, version, listings.
    await db.scalars(select(User).where(User.id.in_(parties)).order_by(User.id).with_for_update())
    await shop_user(db, principal.user_id, manage=True, write=True)
    selected = set(body.relation_ids)
    if body.audience_all:
        selected.update(row.relation_id for row in rows if row.relation_id is not None)
    changed_relations = selected - {row.relation_id for row in rows}
    changed_relations.update(
        row.relation_id
        for row in rows
        if row.relation_id is not None
        and (
            row.audience_all != body.audience_all
            or row.active != (row.relation_id in selected)
            or (row.relation_id in selected and row.price != body.price)
        )
    )
    for rid in sorted(changed_relations):
        await e.relation(db, rid, principal.user_id, write=True)
    await db.get(RewardVersion, body.reward_version_id, with_for_update=True)
    rows = list(
        (
            await db.scalars(
                select(ShopListing)
                .where(ShopListing.reward_version_id == body.reward_version_id)
                .order_by(ShopListing.id)
                .with_for_update()
                .execution_options(populate_existing=True)
            )
        ).all()
    )
    if {row.id: row.revision for row in rows} != {
        row.id: row.expected_version for row in body.existing
    }:
        raise AppError(409, "VERSION_CONFLICT")
    await shop_user(db, principal.user_id, manage=True, write=True)
    selected = set(body.relation_ids)
    if body.audience_all:
        selected.update(row.relation_id for row in rows if row.relation_id is not None)
    for row in rows:
        active = row.relation_id in selected
        price = body.price if active else row.price
        if row.active != active or row.price != price or row.audience_all != body.audience_all:
            row.active, row.price, row.audience_all = active, price, body.audience_all
            row.revision += 1
    for rid in sorted(selected - {row.relation_id for row in rows}):
        row = ShopListing(
            id=uuid4(),
            relation_id=rid,
            reward_version_id=body.reward_version_id,
            price=body.price,
            audience_all=body.audience_all,
        )
        db.add(row)
        rows.append(row)
    await db.flush()
    return [
        await e.listing_view(db, row, cipher_for(request))
        for row in sorted(rows, key=lambda row: row.id)
    ]
