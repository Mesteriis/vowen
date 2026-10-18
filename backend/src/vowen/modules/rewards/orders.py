"""Purchase reservation, explicit approval and single redemption."""

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from vowen.core.crypto import PayloadCipher
from vowen.core.errors import AppError
from vowen.modules.identity.models import User
from vowen.modules.relations.models import Relation
from vowen.modules.rewards import economy, service
from vowen.modules.rewards.economy_models import (
    CurrencyEntry,
    PurchaseOrder,
    ShopListing,
    ShopRelationPreference,
)
from vowen.modules.rewards.economy_schemas import PurchaseCommand
from vowen.modules.rewards.models import RewardDefinition, RewardGrant, RewardVersion
from vowen.modules.rewards.permissions import shop_user
from vowen.modules.rewards.schemas import GrantTransitionCommand, GrantView
from vowen.modules.rituals.service import scoped


async def request_purchase(
    db: AsyncSession,
    sid: UUID,
    uid: UUID,
    body: PurchaseCommand,
    now: datetime,
    cipher: PayloadCipher,
) -> GrantView:
    user = await shop_user(db, uid, write=True)
    if user.shop_role not in {"bottom", "switch"}:
        raise AppError(403, "ACCESS_DENIED")
    listing = await db.get(ShopListing, sid)
    if listing is None:
        raise AppError(404, "NOT_FOUND")
    rid = body.relation_id
    if rid is None:
        candidates = list(
            await db.scalars(
                select(Relation).where(
                    Relation.submissive_user_id == uid, Relation.status == "active"
                )
            )
        )
        candidates = [
            r
            for r in candidates
            if await scoped(db, r.dominant_user_id, uid, "rewards.grant", {r.dominant_user_id})
        ]
        if len(candidates) != 1:
            raise AppError(422, "RELATION_REQUIRED")
        rid = candidates[0].id
    relation = await economy.relation(db, rid, uid, write=True)
    if relation.submissive_user_id != uid:
        raise AppError(403, "ACCESS_DENIED")
    issuer = await db.get(User, relation.dominant_user_id)
    if issuer is None or issuer.shop_role not in {"dominant", "switch"}:
        raise AppError(403, "ACCESS_DENIED")
    # Role changes serialize on the same user lock as wallet operations.
    await db.refresh(user)
    if user.shop_role not in {"bottom", "switch"}:
        raise AppError(403, "ACCESS_DENIED")
    await economy.locked_wallet(db, rid)
    previous = await db.scalar(
        select(PurchaseOrder).where(
            PurchaseOrder.relation_id == rid,
            PurchaseOrder.buyer_id == uid,
            PurchaseOrder.idempotency_key == body.idempotency_key,
        )
    )
    if previous:
        if previous.listing_id != sid:
            raise AppError(409, "IDEMPOTENCY_CONFLICT")
        grant = await db.get(RewardGrant, previous.grant_id)
        assert grant is not None
        return await service.grant_view(db, grant, cipher)
    legacy = await db.scalar(
        select(CurrencyEntry).where(
            CurrencyEntry.relation_id == rid,
            CurrencyEntry.actor_id == uid,
            CurrencyEntry.idempotency_key == body.idempotency_key,
        )
    )
    if legacy:
        if legacy.kind != "purchase" or legacy.listing_id != sid:
            raise AppError(409, "IDEMPOTENCY_CONFLICT")
        previous_grant = await db.get(RewardGrant, legacy.grant_id)
        assert previous_grant is not None
        return await service.grant_view(db, previous_grant, cipher)
    version = await db.get(RewardVersion, listing.reward_version_id)
    assert version is not None
    definition = await db.get(RewardDefinition, version.definition_id, with_for_update=True)
    assert definition is not None
    listing = await db.get(ShopListing, sid, with_for_update=True, populate_existing=True)
    assert listing is not None
    preference = await db.get(ShopRelationPreference, (rid, definition.id), populate_existing=True)
    visible = (
        listing.audience_all
        or listing.relation_id == rid
        or (preference is not None and preference.enabled)
    )
    if (
        not visible
        or definition.shop_deleted
        or not definition.shop_enabled
        or (preference is not None and not preference.enabled)
    ):
        raise AppError(403, "ACCESS_DENIED")
    if not listing.active or listing.revision != body.expected_version:
        raise AppError(409, "LISTING_CHANGED")
    if await economy.available_balance(db, rid) < listing.price:
        raise AppError(409, "INSUFFICIENT_BALANCE")
    grant = RewardGrant(
        id=uuid4(),
        reward_version_id=listing.reward_version_id,
        recipient_id=uid,
        issuer_id=relation.dominant_user_id,
        idempotency_key=uuid4(),
        revision=1,
        status="pending_approval",
        created_at=now,
    )
    db.add(grant)
    await db.flush()
    db.add(
        PurchaseOrder(
            grant_id=grant.id,
            relation_id=rid,
            listing_id=sid,
            buyer_id=uid,
            amount=listing.price,
            idempotency_key=body.idempotency_key,
        )
    )
    await db.flush()
    await service.record(db, grant, uid, now)
    return await service.grant_view(db, grant, cipher)


async def transition(
    db: AsyncSession,
    gid: UUID,
    uid: UUID,
    body: GrantTransitionCommand,
    now: datetime,
    cipher: PayloadCipher,
) -> GrantView:
    order = await db.get(PurchaseOrder, gid)
    grant = await db.get(RewardGrant, gid)
    if order is None or grant is None or uid not in {grant.issuer_id, grant.recipient_id}:
        raise AppError(404, "NOT_FOUND")
    await db.scalars(
        select(User)
        .where(User.id.in_([grant.issuer_id, grant.recipient_id]))
        .order_by(User.id)
        .execution_options(populate_existing=True)
        .with_for_update()
    )
    if body.action == "approve":
        if uid != grant.issuer_id:
            raise AppError(403, "ACCESS_DENIED")
        issuer = await shop_user(db, uid, write=True)
        buyer = await db.get(User, grant.recipient_id, populate_existing=True)
        if (
            issuer.shop_role not in {"dominant", "switch"}
            or not buyer
            or buyer.shop_role not in {"bottom", "switch"}
        ):
            raise AppError(403, "ACCESS_DENIED")
        await economy.relation(db, order.relation_id, uid, write=True)
    elif body.action == "reject":
        if uid != grant.issuer_id:
            raise AppError(403, "ACCESS_DENIED")
    elif body.action == "cancel":
        if uid != grant.recipient_id:
            raise AppError(403, "ACCESS_DENIED")
    elif body.action != "redeem":
        raise AppError(409, "CONFLICT")
    await economy.locked_wallet(db, order.relation_id)
    grant = await db.get(RewardGrant, gid, with_for_update=True, populate_existing=True)
    assert grant is not None
    if grant.revision != body.expected_version:
        raise AppError(409, "VERSION_CONFLICT")
    expected = "accepted" if body.action == "redeem" else "pending_approval"
    if grant.status != expected:
        raise AppError(409, "CONFLICT")
    if body.action == "approve":
        if await economy.balance(db, order.relation_id) < order.amount:
            raise AppError(409, "INSUFFICIENT_BALANCE")
        await economy.append(
            db,
            order.relation_id,
            grant.recipient_id,
            -order.amount,
            "purchase",
            "",
            now,
            cipher,
            key=order.idempotency_key,
            grant_id=gid,
            listing_id=order.listing_id,
        )
    grant.status = {
        "approve": "accepted",
        "reject": "declined",
        "cancel": "cancelled",
        "redeem": "redeemed",
    }[body.action]
    grant.revision += 1
    await service.record(db, grant, uid, now)
    await db.flush()
    return await service.grant_view(db, grant, cipher)
