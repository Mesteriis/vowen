import json
from datetime import datetime
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
    RewardTransition,
    RewardVersion,
)
from vowen.modules.rewards.schemas import GrantHistory, GrantView, RewardContent, RewardView
from vowen.modules.rituals.models import RitualAssignment, RitualOccurrence
from vowen.modules.rituals.service import scoped


def opened(v: RewardVersion, cipher: PayloadCipher) -> dict[str, str]:
    result: dict[str, str] = json.loads(
        cipher.open_payload(
            "reward_version", v.id, 1, EncryptedEnvelope(v.key_id, v.nonce, v.ciphertext)
        )
    )
    return result


async def new_version(
    db: AsyncSession, r: RewardDefinition, body: RewardContent, cipher: PayloadCipher
) -> RewardView:
    v = RewardVersion(id=uuid4(), definition_id=r.id)
    e = cipher.seal_payload(
        "reward_version",
        v.id,
        1,
        json.dumps(body.model_dump(include={"title", "description", "conditions"})).encode(),
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


async def configure(db: AsyncSession, a: RitualAssignment, vid: UUID, now: datetime) -> None:
    await owned_version(db, vid, a.issuer_id)
    if not await scoped(db, a.issuer_id, a.recipient_id, "rewards.grant", {a.issuer_id}):
        raise AppError(403, "ACCESS_DENIED")
    p = RewardPolicy(
        id=uuid4(), assignment_id=a.id, reward_version_id=vid, issuer_id=a.issuer_id, created_at=now
    )
    db.add(p)
    await db.flush()
    a.reward_policy_id = p.id


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


async def award(db: AsyncSession, a: RitualAssignment, o: RitualOccurrence, now: datetime) -> None:
    if o.status != "approved" or o.reward_policy_id is None:
        return
    p = await db.get(RewardPolicy, o.reward_policy_id)
    assert p is not None
    if not await scoped(db, p.issuer_id, a.recipient_id, "rewards.grant", {p.issuer_id}):
        return
    gid = uuid4()
    created = await db.scalar(
        insert(RewardGrant)
        .values(
            id=gid,
            reward_version_id=p.reward_version_id,
            issuer_id=p.issuer_id,
            recipient_id=a.recipient_id,
            occurrence_id=o.id,
            reward_policy_id=p.id,
            revision=1,
            status="offered",
            created_at=now,
        )
        .on_conflict_do_nothing()
        .returning(RewardGrant.id)
    )
    if created:
        g = await db.get(RewardGrant, gid)
        assert g is not None
        await record(db, g, p.issuer_id, now)


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
    return GrantView(
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
