"""Relationship-scoped ledger and shop. All effects share the request transaction."""

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from vowen.core.crypto import EncryptedEnvelope, PayloadCipher
from vowen.core.errors import AppError
from vowen.modules.identity.models import User
from vowen.modules.relations.models import Relation
from vowen.modules.rewards.economy_models import CurrencyEntry, ShopListing, Wallet
from vowen.modules.rewards.economy_schemas import CurrencyEntryView, ListingView, WalletView
from vowen.modules.rewards.models import RewardVersion
from vowen.modules.rituals.service import scoped


async def relation(db: AsyncSession, rid: UUID, uid: UUID, *, write: bool = False) -> Relation:
    r = await db.get(Relation, rid)
    if r is None or uid not in (r.dominant_user_id, r.submissive_user_id):
        raise AppError(404, "NOT_FOUND")
    if write:
        # Same order as relationship transitions: parties, relation, then wallet.
        await db.scalars(
            select(User)
            .where(User.id.in_([r.dominant_user_id, r.submissive_user_id]))
            .order_by(User.id)
            .with_for_update()
        )
        r = await db.get(Relation, rid, with_for_update=True, populate_existing=True)
        assert r is not None
        if r.status != "active" or not await scoped(
            db, r.dominant_user_id, r.submissive_user_id, "rewards.grant", {r.dominant_user_id}
        ):
            raise AppError(403, "ACCESS_DENIED")
    return r


async def locked_wallet(db: AsyncSession, rid: UUID) -> None:
    await db.execute(insert(Wallet).values(relation_id=rid).on_conflict_do_nothing())
    await db.get(Wallet, rid, with_for_update=True)


async def balance(db: AsyncSession, rid: UUID) -> int:
    return int(
        await db.scalar(
            select(func.coalesce(func.sum(CurrencyEntry.amount), 0)).where(
                CurrencyEntry.relation_id == rid
            )
        )
        or 0
    )


def comment(e: CurrencyEntry, cipher: PayloadCipher) -> str:
    return cipher.open_payload(
        "currency_entry", e.id, 1, EncryptedEnvelope(e.key_id, e.nonce, e.ciphertext)
    ).decode()


async def wallet_view(db: AsyncSession, rid: UUID, cipher: PayloadCipher) -> WalletView:
    entries = (
        await db.scalars(
            select(CurrencyEntry)
            .where(CurrencyEntry.relation_id == rid)
            .order_by(CurrencyEntry.created_at.desc(), CurrencyEntry.id.desc())
            .limit(500)
        )
    ).all()
    return WalletView(
        relation_id=rid,
        balance=await balance(db, rid),
        entries=[
            CurrencyEntryView(
                id=e.id,
                amount=e.amount,
                kind=e.kind,
                comment=comment(e, cipher),
                actor_id=e.actor_id,
                occurrence_id=e.occurrence_id,
                grant_id=e.grant_id,
                created_at=e.created_at,
            )
            for e in entries
        ],
    )


async def append(
    db: AsyncSession,
    rid: UUID,
    uid: UUID,
    amount: int,
    kind: str,
    text: str,
    now: datetime,
    cipher: PayloadCipher,
    *,
    key: UUID | None = None,
    occurrence_id: UUID | None = None,
    policy_id: UUID | None = None,
    grant_id: UUID | None = None,
    listing_id: UUID | None = None,
) -> CurrencyEntry:
    if not 0 <= await balance(db, rid) + amount <= 9007199254740991:
        raise AppError(409, "BALANCE_LIMIT")
    e = CurrencyEntry(
        id=uuid4(),
        relation_id=rid,
        actor_id=uid,
        amount=amount,
        kind=kind,
        idempotency_key=key,
        occurrence_id=occurrence_id,
        policy_id=policy_id,
        grant_id=grant_id,
        listing_id=listing_id,
        created_at=now,
    )
    sealed = cipher.seal_payload("currency_entry", e.id, 1, text.encode())
    e.key_id, e.nonce, e.ciphertext = sealed.key_id, sealed.nonce, sealed.ciphertext
    db.add(e)
    await db.flush()
    return e


async def listing_view(
    db: AsyncSession, listing: ShopListing, cipher: PayloadCipher
) -> ListingView:
    from vowen.modules.rewards.service import opened

    v = await db.get(RewardVersion, listing.reward_version_id)
    assert v is not None
    return ListingView(
        id=listing.id,
        relation_id=listing.relation_id,
        reward_version_id=v.id,
        price=listing.price,
        active=listing.active,
        revision=listing.revision,
        **opened(v, cipher),
    )
