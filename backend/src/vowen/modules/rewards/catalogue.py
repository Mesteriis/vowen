"""Global product management and explicit per-relationship availability."""

from uuid import UUID, uuid4

from fastapi import APIRouter, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from vowen.core.crypto import PayloadCipher
from vowen.core.errors import AppError
from vowen.modules.auth.router import DB, Member
from vowen.modules.relations.models import Relation
from vowen.modules.relations.router import cipher_for
from vowen.modules.rewards import economy, service
from vowen.modules.rewards.economy_models import ShopListing, ShopRelationPreference
from vowen.modules.rewards.economy_schemas import (
    ListingView,
    ProductRevision,
    ProductStateCommand,
    RelationProductCommand,
)
from vowen.modules.rewards.models import RewardDefinition, RewardVersion
from vowen.modules.rewards.permissions import shop_user
from vowen.modules.rewards.schemas import RewardContent, ShopProductContent, ShopProductEdit
from vowen.modules.rituals.service import scoped

router = APIRouter(prefix="/api/v1")


async def listing_catalogue(
    db: AsyncSession, uid: UUID, cipher: PayloadCipher, selected: UUID | None = None
) -> list[ListingView]:
    user = await shop_user(db, uid)
    if selected is not None:
        await economy.relation(db, selected, uid)
    direct = list(
        await db.scalars(
            select(Relation).where(
                (Relation.dominant_user_id == uid) | (Relation.submissive_user_id == uid)
            )
        )
    )
    eligible = []
    for relation in direct:
        if relation.status == "active" and await scoped(
            db,
            relation.dominant_user_id,
            relation.submissive_user_id,
            "rewards.grant",
            {relation.dominant_user_id},
        ):
            eligible.append(relation)
    lower = [r for r in eligible if r.submissive_user_id == uid]
    upper = [r for r in eligible if r.dominant_user_id == uid]

    def choose(rows: list[Relation]) -> Relation | None:
        if selected:
            return next((r for r in rows if r.id == selected), None)
        return rows[0] if len(rows) == 1 else None

    buyer = choose(lower) if user.shop_role in {"bottom", "switch"} else None
    controller = (
        choose(upper) if user.shop_role in {"dominant", "switch"} and buyer is None else None
    )
    context = buyer or controller
    manager = user.shop_role == "dominant"
    rows = (
        await db.execute(
            select(ShopListing, RewardDefinition)
            .join(RewardVersion, RewardVersion.id == ShopListing.reward_version_id)
            .join(RewardDefinition, RewardDefinition.id == RewardVersion.definition_id)
            .where(~RewardDefinition.shop_deleted)
            .where(ShopListing.active | (RewardDefinition.current_version_id == RewardVersion.id))
            .order_by(ShopListing.id)
        )
    ).all()
    result: dict[UUID, ListingView] = {}
    ranks: dict[UUID, tuple[bool, bool]] = {}
    for listing, definition in rows:
        preference = (
            await db.get(ShopRelationPreference, (context.id, definition.id)) if context else None
        )
        personal = (context is not None and listing.relation_id == context.id) or (
            preference is not None and (preference.enabled or controller is not None)
        )
        globally_enabled = definition.shop_enabled and listing.active
        relation_enabled = preference.enabled if preference else True
        if not manager:
            if not globally_enabled or not (listing.audience_all or personal):
                continue
            if buyer and not relation_enabled:
                continue
        item = await economy.listing_view(db, listing, cipher)
        item.product_id, item.product_revision = definition.id, definition.revision
        item.author_id = definition.author_id
        item.global_enabled = globally_enabled
        item.relation_enabled = relation_enabled
        item.active = globally_enabled and relation_enabled
        item.can_manage = manager and not user.paused
        item.can_toggle = controller is not None and not user.paused
        item.toggle_relation_id = controller.id if controller else None
        item.toggle_revision = preference.revision if preference else 0
        item.purchase_relation_id = buyer.id if buyer and item.active and not user.paused else None
        item.relation_id = context.id if context else None
        rank = (listing.reward_version_id == definition.current_version_id, listing.active)
        if definition.id not in result or rank > ranks[definition.id]:
            result[definition.id], ranks[definition.id] = item, rank
    return list(result.values())


async def manager_item(
    db: AsyncSession, definition: RewardDefinition, listing: ShopListing, cipher: PayloadCipher
) -> ListingView:
    item = await economy.listing_view(db, listing, cipher)
    item.product_id, item.product_revision = definition.id, definition.revision
    item.author_id, item.can_manage = definition.author_id, True
    item.global_enabled = definition.shop_enabled and listing.active
    item.active = item.global_enabled
    item.relation_id = None
    return item


@router.post("/shop/products", response_model=ListingView)
async def create_product(
    body: ShopProductContent, principal: Member, db: DB, request: Request
) -> ListingView:
    await shop_user(db, principal.user_id, manage=True, write=True, lock=True)
    definition = RewardDefinition(id=uuid4(), author_id=principal.user_id, revision=1)
    db.add(definition)
    await db.flush()
    content = RewardContent.model_validate(body.model_dump(exclude={"price", "audience_all"}))
    version = await service.new_version(db, definition, content, cipher_for(request))
    listing = ShopListing(
        id=uuid4(),
        relation_id=None,
        reward_version_id=version.version_id,
        price=body.price,
        audience_all=body.audience_all,
    )
    db.add(listing)
    await db.flush()
    return await manager_item(db, definition, listing, cipher_for(request))


@router.patch("/shop/products/{pid}", response_model=ListingView)
async def edit_product(
    pid: UUID, body: ShopProductEdit, principal: Member, db: DB, request: Request
) -> ListingView:
    await shop_user(db, principal.user_id, manage=True, write=True, lock=True)
    definition = await db.get(RewardDefinition, pid, with_for_update=True)
    if definition is None or definition.shop_deleted:
        raise AppError(404, "NOT_FOUND")
    if definition.revision != body.expected_version:
        raise AppError(409, "VERSION_CONFLICT")
    definition.revision += 1
    content = RewardContent.model_validate(
        body.model_dump(exclude={"price", "audience_all", "expected_version"})
    )
    version = await service.new_version(db, definition, content, cipher_for(request))
    old = list(
        await db.scalars(
            select(ShopListing)
            .join(RewardVersion, RewardVersion.id == ShopListing.reward_version_id)
            .where(RewardVersion.definition_id == pid, ShopListing.active)
            .with_for_update(of=ShopListing)
        )
    )
    relations = {row.relation_id for row in old} or {None}
    for row in old:
        row.active = False
        row.revision += 1
    replacements = []
    for rid in relations:
        listing = ShopListing(
            id=uuid4(),
            relation_id=rid,
            reward_version_id=version.version_id,
            price=body.price,
            audience_all=body.audience_all,
        )
        db.add(listing)
        replacements.append(listing)
    await db.flush()
    return await manager_item(db, definition, replacements[0], cipher_for(request))


@router.post("/shop/products/{pid}/state", response_model=ProductStateCommand)
async def product_state(
    pid: UUID, body: ProductStateCommand, principal: Member, db: DB
) -> ProductStateCommand:
    await shop_user(db, principal.user_id, manage=True, write=True, lock=True)
    definition = await db.get(RewardDefinition, pid, with_for_update=True)
    if definition is None or definition.shop_deleted:
        raise AppError(404, "NOT_FOUND")
    if definition.revision != body.expected_version:
        raise AppError(409, "VERSION_CONFLICT")
    definition.shop_enabled = body.enabled
    definition.revision += 1
    return ProductStateCommand(
        expected_version=definition.revision, enabled=definition.shop_enabled
    )


@router.post("/shop/products/{pid}/archive", status_code=204)
async def archive_product(pid: UUID, body: ProductRevision, principal: Member, db: DB) -> None:
    await shop_user(db, principal.user_id, manage=True, write=True, lock=True)
    definition = await db.get(RewardDefinition, pid, with_for_update=True)
    if definition is None:
        raise AppError(404, "NOT_FOUND")
    if definition.revision != body.expected_version:
        raise AppError(409, "VERSION_CONFLICT")
    definition.shop_deleted = True
    definition.shop_enabled = False
    definition.revision += 1


@router.post("/relations/{rid}/shop/products/{pid}/state", response_model=RelationProductCommand)
async def relation_state(
    rid: UUID, pid: UUID, body: RelationProductCommand, principal: Member, db: DB
) -> RelationProductCommand:
    user = await shop_user(db, principal.user_id, write=True)
    if user.shop_role not in {"dominant", "switch"}:
        raise AppError(403, "ACCESS_DENIED")
    relation = await economy.relation(db, rid, principal.user_id, write=True)
    if relation.dominant_user_id != principal.user_id:
        raise AppError(403, "ACCESS_DENIED")
    user = await shop_user(db, principal.user_id, write=True)
    if user.shop_role not in {"dominant", "switch"}:
        raise AppError(403, "ACCESS_DENIED")
    definition = await db.get(RewardDefinition, pid)
    if definition is None or definition.shop_deleted:
        raise AppError(404, "NOT_FOUND")
    preference = await db.get(ShopRelationPreference, (rid, pid), with_for_update=True)
    if user.shop_role == "switch" and preference is None:
        # A guessed private product ID cannot create a new visibility grant.
        visible = await db.scalar(
            select(ShopListing.id)
            .join(RewardVersion, RewardVersion.id == ShopListing.reward_version_id)
            .where(
                RewardVersion.definition_id == pid,
                ShopListing.active,
                ShopListing.audience_all | (ShopListing.relation_id == rid),
            )
            .limit(1)
        )
        if visible is None:
            raise AppError(404, "NOT_FOUND")
    if body.expected_version != (preference.revision if preference else 0):
        raise AppError(409, "VERSION_CONFLICT")
    if preference is None:
        preference = ShopRelationPreference(
            relation_id=rid, definition_id=pid, enabled=body.enabled, revision=1
        )
        db.add(preference)
    else:
        preference.enabled = body.enabled
        preference.revision += 1
    await db.flush()
    return RelationProductCommand(expected_version=preference.revision, enabled=preference.enabled)
