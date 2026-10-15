import json
from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from vowen.core.crypto import EncryptedEnvelope, PayloadCipher
from vowen.core.errors import AppError
from vowen.modules.discipline.models import (
    DisciplineRecord,
    DisciplineReviewer,
    DisciplineTransition,
    DisciplineVersion,
)
from vowen.modules.discipline.schemas import (
    DisciplineContent,
    DisciplineHistory,
    DisciplineVersionView,
    DisciplineView,
)
from vowen.modules.identity.models import User
from vowen.modules.relations.models import Relation
from vowen.modules.rituals.service import scoped
from vowen.modules.rules.models import RuleAssignment, RuleVersion
from vowen.modules.rules.service import content as rule_content


def seal(row: DisciplineVersion | DisciplineTransition, value: str, cipher: PayloadCipher) -> None:
    kind = "discipline_version" if isinstance(row, DisciplineVersion) else "discipline_transition"
    e = cipher.seal_payload(kind, row.id, 1, value.encode())
    row.key_id, row.nonce, row.ciphertext = e.key_id, e.nonce, e.ciphertext


def opened(row: DisciplineVersion | DisciplineTransition, cipher: PayloadCipher) -> str:
    kind = "discipline_version" if isinstance(row, DisciplineVersion) else "discipline_transition"
    return cipher.open_payload(
        kind, row.id, 1, EncryptedEnvelope(row.key_id, row.nonce, row.ciphertext)
    ).decode()


async def reviewers(db: AsyncSession, r: DisciplineRecord) -> list[UUID]:
    return list(
        await db.scalars(
            select(DisciplineReviewer.user_id)
            .where(DisciplineReviewer.record_id == r.id)
            .order_by(DisciplineReviewer.user_id)
        )
    )


async def permitted(db: AsyncSession, uid: UUID, target: UUID, scope: str) -> bool:
    return await scoped(db, uid, target, scope, {uid})


async def visible(db: AsyncSession, r: DisciplineRecord, uid: UUID) -> bool:
    if uid == r.recipient_id:
        return True
    if uid == r.author_id and await permitted(db, uid, r.recipient_id, "discipline.propose"):
        return True
    return uid in await reviewers(db, r) and await permitted(
        db, uid, r.recipient_id, "discipline.review"
    )


async def lock_authority(db: AsyncSession, target: UUID, actors: list[UUID]) -> None:
    # Match current relation and member locks before evaluating authorization.
    await db.scalars(
        select(Relation)
        .where(Relation.submissive_user_id == target, Relation.dominant_user_id.in_(actors))
        .order_by(Relation.id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    await db.scalars(
        select(User)
        .where(User.id.in_([target, *actors]))
        .order_by(User.id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )


async def locked(db: AsyncSession, rid: UUID, uid: UUID) -> DisciplineRecord:
    r = await db.get(DisciplineRecord, rid, with_for_update=True)
    if r is None:
        raise AppError(404, "NOT_FOUND")
    await lock_authority(db, r.recipient_id, [r.author_id, *await reviewers(db, r)])
    if not await visible(db, r, uid):
        raise AppError(404, "NOT_FOUND")
    return r


async def validate_links(
    db: AsyncSession, r: DisciplineRecord, body: DisciplineContent, cipher: PayloadCipher
) -> str | None:
    title = None
    if body.rule_version_id is not None:
        a = await db.scalar(
            select(RuleAssignment).where(
                RuleAssignment.rule_version_id == body.rule_version_id,
                RuleAssignment.recipient_id == r.recipient_id,
                RuleAssignment.accepted_at.is_not(None),
            )
        )
        if a is None:
            raise AppError(403, "ACCESS_DENIED")
        # A discipline proposal cannot open another participant's rule template.
        from vowen.modules.rules.service import visible as rule_visible

        if not await rule_visible(db, a, r.author_id):
            raise AppError(403, "ACCESS_DENIED")
        v = await db.get(RuleVersion, body.rule_version_id)
        assert v is not None
        title = rule_content(v, cipher).title
    if body.occurrence_id is not None:
        from vowen.modules.rituals.models import RitualAssignment, RitualOccurrence
        from vowen.modules.rituals.service import visible as ritual_visible

        o = await db.get(RitualOccurrence, body.occurrence_id)
        a_ritual = await db.get(RitualAssignment, o.assignment_id) if o else None
        if (
            a_ritual is None
            or a_ritual.recipient_id != r.recipient_id
            or not await ritual_visible(db, a_ritual, r.author_id)
        ):
            raise AppError(403, "ACCESS_DENIED")
    return title


async def version(
    db: AsyncSession,
    r: DisciplineRecord,
    body: DisciplineContent,
    cipher: PayloadCipher,
    now: datetime,
) -> None:
    title = await validate_links(db, r, body, cipher)
    v = DisciplineVersion(
        id=uuid4(),
        record_id=r.id,
        rule_version_id=body.rule_version_id,
        occurrence_id=body.occurrence_id,
        created_at=now,
    )
    seal(v, json.dumps({**body.model_dump(mode="json"), "rule_title": title}), cipher)
    db.add(v)
    await db.flush()
    r.current_version_id = v.id
    r.status = "proposed"


async def event(
    db: AsyncSession,
    r: DisciplineRecord,
    uid: UUID,
    comment: str,
    cipher: PayloadCipher,
    now: datetime,
) -> None:
    assert r.current_version_id is not None
    e = DisciplineTransition(
        id=uuid4(),
        record_id=r.id,
        version_id=r.current_version_id,
        revision=r.revision,
        status=r.status,
        actor_id=uid,
        created_at=now,
    )
    seal(e, comment, cipher)
    db.add(e)
    await db.flush()


async def view(db: AsyncSession, r: DisciplineRecord, cipher: PayloadCipher) -> DisciplineView:
    versions = (
        await db.scalars(
            select(DisciplineVersion)
            .where(DisciplineVersion.record_id == r.id)
            .order_by(DisciplineVersion.created_at, DisciplineVersion.id)
        )
    ).all()
    events = (
        await db.scalars(
            select(DisciplineTransition)
            .where(DisciplineTransition.record_id == r.id)
            .order_by(DisciplineTransition.revision)
        )
    ).all()
    positions = {e.version_id: e.revision for e in reversed(events)}
    versions = sorted(versions, key=lambda v: positions[v.id])
    assert r.current_version_id is not None
    return DisciplineView.model_validate(
        dict(
            id=r.id,
            author_id=r.author_id,
            recipient_id=r.recipient_id,
            reviewer_ids=await reviewers(db, r),
            version_id=r.current_version_id,
            revision=r.revision,
            status=r.status,
            effective=r.status in ("accepted", "in_progress", "completed")
            and await permitted(db, r.author_id, r.recipient_id, "discipline.propose"),
            versions=[
                DisciplineVersionView(
                    id=v.id, created_at=v.created_at, **json.loads(opened(v, cipher))
                )
                for v in versions
            ],
            history=[
                DisciplineHistory.model_validate(
                    dict(
                        revision=e.revision,
                        version_id=e.version_id,
                        actor_id=e.actor_id,
                        status=e.status,
                        created_at=e.created_at,
                        comment=opened(e, cipher),
                    )
                )
                for e in events
            ],
        )
    )
