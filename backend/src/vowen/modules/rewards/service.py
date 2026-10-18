import json
from datetime import datetime
from typing import TypedDict
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from vowen.core.crypto import EncryptedEnvelope, PayloadCipher
from vowen.core.errors import AppError
from vowen.modules.rewards.models import (
    RewardDefinition,
    RewardGrant,
    RewardNotice,
    RewardPolicy,
    RewardPolicyItem,
    RewardTransition,
    RewardVersion,
)
from vowen.modules.rewards.schemas import (
    GrantHistory,
    GrantView,
    RewardCategory,
    RewardContent,
    RewardCover,
    RewardView,
)
from vowen.modules.rituals.models import RitualAssignment, RitualOccurrence


class RewardPayload(TypedDict):
    title: str
    description: str
    conditions: str
    cover: RewardCover
    category: RewardCategory


def opened(v: RewardVersion, cipher: PayloadCipher) -> RewardPayload:
    content = RewardContent.model_validate_json(
        cipher.open_payload(
            "reward_version", v.id, 1, EncryptedEnvelope(v.key_id, v.nonce, v.ciphertext)
        )
    )
    return {
        "title": content.title,
        "description": content.description,
        "conditions": content.conditions,
        "cover": content.cover,
        "category": content.category,
    }


async def new_version(
    db: AsyncSession, r: RewardDefinition, body: RewardContent, cipher: PayloadCipher
) -> RewardView:
    v = RewardVersion(id=uuid4(), definition_id=r.id)
    e = cipher.seal_payload(
        "reward_version",
        v.id,
        1,
        json.dumps(
            body.model_dump(include={"title", "description", "conditions", "cover", "category"})
        ).encode(),
    )
    v.key_id, v.nonce, v.ciphertext = e.key_id, e.nonce, e.ciphertext
    db.add(v)
    await db.flush()
    r.current_version_id = v.id
    return RewardView(id=r.id, version_id=v.id, revision=r.revision, **opened(v, cipher))


async def owned_version(db: AsyncSession, vid: UUID, uid: UUID) -> RewardVersion:
    v = await db.get(RewardVersion, vid)
    r = await db.get(RewardDefinition, v.definition_id) if v else None
    if v is None or r is None or r.author_id != uid:
        raise AppError(404, "NOT_FOUND")
    return v


async def configure(
    db: AsyncSession,
    a: RitualAssignment,
    vids: list[UUID],
    amount: int,
    now: datetime,
    *,
    automatic_accept: bool = True,
) -> None:
    from vowen.modules.relations.models import Relation
    from vowen.modules.rewards.economy import relation

    for vid in vids:
        await owned_version(db, vid, a.issuer_id)
    r = await db.scalar(
        select(Relation).where(
            Relation.dominant_user_id == a.issuer_id,
            Relation.submissive_user_id == a.recipient_id,
            Relation.status == "active",
        )
    )
    if r is None:
        raise AppError(403, "ACCESS_DENIED")
    await relation(db, r.id, a.issuer_id, write=True)
    p = RewardPolicy(
        id=uuid4(),
        assignment_id=a.id,
        reward_version_id=vids[0] if vids else None,
        issuer_id=a.issuer_id,
        relation_id=r.id,
        currency_amount=amount,
        automatic_accept=automatic_accept,
        created_at=now,
    )
    db.add(p)
    await db.flush()
    db.add_all(
        [RewardPolicyItem(id=uuid4(), policy_id=p.id, reward_version_id=vid) for vid in vids]
    )
    await db.flush()
    a.reward_policy_id = p.id


async def bundle(db: AsyncSession, pid: UUID | None) -> tuple[list[UUID], int]:
    if pid is None:
        return [], 0
    p = await db.get(RewardPolicy, pid)
    assert p is not None
    ids = list(
        await db.scalars(
            select(RewardPolicyItem.reward_version_id)
            .where(RewardPolicyItem.policy_id == pid)
            .order_by(RewardPolicyItem.id)
        )
    )
    return ids, p.currency_amount


async def record(db: AsyncSession, g: RewardGrant, uid: UUID, now: datetime) -> None:
    db.add(
        RewardTransition(
            id=uuid4(),
            grant_id=g.id,
            revision=g.revision,
            status=g.status,
            actor_id=uid,
            created_at=now,
        )
    )
    from vowen.modules.notifications.delivery import enqueue

    for target in {g.recipient_id, g.issuer_id}:
        nid = uuid4()
        db.add(
            RewardNotice(id=nid, grant_id=g.id, user_id=target, revision=g.revision, created_at=now)
        )
        await db.flush()
        await enqueue(db, target, now, reward_notice_id=nid)


async def award(
    db: AsyncSession,
    a: RitualAssignment,
    o: RitualOccurrence,
    now: datetime,
    cipher: PayloadCipher,
) -> None:
    if o.status != "approved" or o.reward_policy_id is None:
        return
    p = await db.get(RewardPolicy, o.reward_policy_id)
    assert p is not None
    if p.relation_id is not None:
        from vowen.modules.rewards import economy

        try:
            await economy.relation(db, p.relation_id, p.issuer_id, write=True)
        except AppError:
            return
    else:
        # Unbound legacy policies cannot acquire authority from a later relationship.
        return
    items = (
        await db.scalars(select(RewardPolicyItem).where(RewardPolicyItem.policy_id == p.id))
    ).all()
    for item in items:
        gid = uuid4()
        created = await db.scalar(
            insert(RewardGrant)
            .values(
                id=gid,
                reward_version_id=item.reward_version_id,
                policy_item_id=item.id,
                issuer_id=p.issuer_id,
                recipient_id=a.recipient_id,
                occurrence_id=o.id,
                reward_policy_id=p.id,
                revision=1,
                status="accepted" if p.automatic_accept else "offered",
                created_at=now,
            )
            .on_conflict_do_nothing()
            .returning(RewardGrant.id)
        )
        if created:
            g = await db.get(RewardGrant, gid)
            assert g is not None
            await record(db, g, p.issuer_id, now)
    if p.currency_amount and p.relation_id is not None:
        from vowen.modules.rewards import economy
        from vowen.modules.rewards.economy_models import CurrencyEntry

        await economy.locked_wallet(db, p.relation_id)
        previous = await db.scalar(
            select(CurrencyEntry.id).where(
                CurrencyEntry.relation_id == p.relation_id,
                CurrencyEntry.occurrence_id == o.id,
                CurrencyEntry.policy_id == p.id,
            )
        )
        if previous is None:
            await economy.append(
                db,
                p.relation_id,
                p.issuer_id,
                p.currency_amount,
                "ritual",
                "",
                now,
                cipher,
                occurrence_id=o.id,
                policy_id=p.id,
            )


async def grant_view(db: AsyncSession, g: RewardGrant, cipher: PayloadCipher) -> GrantView:
    v = await db.get(RewardVersion, g.reward_version_id)
    assert v is not None
    rows = (
        await db.scalars(
            select(RewardTransition)
            .where(RewardTransition.grant_id == g.id)
            .order_by(RewardTransition.revision)
        )
    ).all()
    from vowen.modules.rewards.economy_models import CurrencyEntry, PurchaseOrder

    order = await db.get(PurchaseOrder, g.id)
    purchased = await db.scalar(
        select(CurrencyEntry.relation_id).where(CurrencyEntry.grant_id == g.id)
    )
    policy = await db.get(RewardPolicy, g.reward_policy_id) if g.reward_policy_id else None
    return GrantView(
        relation_id=order.relation_id if order else policy.relation_id if policy else purchased,
        purchase_amount=order.amount if order else None,
        source="ritual" if g.occurrence_id else "purchase" if purchased or order else "manual",
        id=g.id,
        reward_version_id=v.id,
        issuer_id=g.issuer_id,
        recipient_id=g.recipient_id,
        occurrence_id=g.occurrence_id,
        reward_policy_id=g.reward_policy_id,
        revision=g.revision,
        status=g.status,
        created_at=g.created_at,
        history=[
            GrantHistory(
                revision=h.revision, status=h.status, actor_id=h.actor_id, created_at=h.created_at
            )
            for h in rows
        ],
        **opened(v, cipher),
    )
