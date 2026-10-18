import json
from datetime import datetime
from typing import Literal
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import load_only

from vowen.core.crypto import EncryptedEnvelope, PayloadCipher
from vowen.core.errors import AppError
from vowen.modules.auth.service import MemberPrincipal
from vowen.modules.notifications.models import MemberDelivery  # noqa: F401
from vowen.modules.relations.policy import ResourceContext, authorize
from vowen.modules.rituals.models import (
    Ritual,
    RitualAssignment,
    RitualEvidence,
    RitualNotice,
    RitualOccurrence,
    RitualReport,
    RitualReviewer,
    RitualSchedule,
    RitualVersion,
)
from vowen.modules.rituals.schemas import (
    EvidencePolicy,
    EvidenceView,
    OccurrenceView,
    RitualAssignmentView,
    RitualContent,
    RitualReportView,
    RitualView,
    Schedule,
)


def seal(row: RitualVersion | RitualReport, payload: dict[str, str], cipher: PayloadCipher) -> None:
    kind = "ritual_version" if isinstance(row, RitualVersion) else "ritual_report"
    e = cipher.seal_payload(kind, row.id, 1, json.dumps(payload).encode())
    row.key_id, row.nonce, row.ciphertext = e.key_id, e.nonce, e.ciphertext


def opened(row: RitualVersion | RitualReport, cipher: PayloadCipher) -> dict[str, str]:
    kind = "ritual_version" if isinstance(row, RitualVersion) else "ritual_report"
    result: dict[str, str] = json.loads(
        cipher.open_payload(
            kind, row.id, 1, EncryptedEnvelope(row.key_id, row.nonce, row.ciphertext)
        )
    )
    return result


async def new_version(
    db: AsyncSession, ritual: Ritual, body: RitualContent, cipher: PayloadCipher
) -> None:
    v = RitualVersion(id=uuid4(), ritual_id=ritual.id)
    seal(v, {"title": body.title, "description": body.description}, cipher)
    db.add(v)
    await db.flush()
    ritual.current_version_id = v.id


async def owned(db: AsyncSession, rid: UUID, uid: UUID, expected: int | None = None) -> Ritual:
    r = await db.get(Ritual, rid, with_for_update=True)
    if r is None or r.author_id != uid:
        raise AppError(404, "NOT_FOUND")
    if expected is not None and r.revision != expected:
        raise AppError(409, "VERSION_CONFLICT")
    return r


async def view(db: AsyncSession, r: Ritual, cipher: PayloadCipher) -> RitualView:
    v = await db.get(RitualVersion, r.current_version_id)
    assert v is not None
    return RitualView(
        id=r.id, version_id=v.id, revision=r.revision, status=v.status, **opened(v, cipher)
    )


async def reviewers(db: AsyncSession, a: RitualAssignment) -> list[UUID]:
    return list(
        await db.scalars(
            select(RitualReviewer.user_id)
            .where(RitualReviewer.assignment_id == a.id)
            .order_by(RitualReviewer.user_id)
        )
    )


async def scoped(db: AsyncSession, uid: UUID, target: UUID, action: str, actors: set[UUID]) -> bool:
    try:
        await authorize(
            db,
            MemberPrincipal(uid, UUID(int=0)),
            action,
            ResourceContext(target, frozenset(actors)),
        )
    except AppError:
        return False
    return True


async def effective(db: AsyncSession, a: RitualAssignment) -> bool:
    return a.status == "active" and await scoped(
        db, a.issuer_id, a.recipient_id, "rituals.assign", {a.issuer_id}
    )


async def can_review(db: AsyncSession, a: RitualAssignment, uid: UUID) -> bool:
    return await scoped(db, uid, a.recipient_id, "rituals.review", set(await reviewers(db, a)))


async def can_manage(db: AsyncSession, a: RitualAssignment, uid: UUID) -> bool:
    return a.issuer_id == uid and await scoped(
        db, uid, a.recipient_id, "rituals.assign", {a.issuer_id}
    )


async def visible(db: AsyncSession, a: RitualAssignment, uid: UUID) -> bool:
    return a.recipient_id == uid or await can_review(db, a, uid)


async def assignment_view(
    db: AsyncSession, a: RitualAssignment, cipher: PayloadCipher
) -> RitualAssignmentView:
    v = await db.get(RitualVersion, a.ritual_version_id)
    schedule = await db.get(RitualSchedule, a.current_schedule_id)
    assert v is not None and schedule is not None
    from vowen.modules.rewards.models import RewardVersion
    from vowen.modules.rewards.service import bundle
    from vowen.modules.rewards.service import opened as reward_opened

    reward_ids, currency = await bundle(db, a.reward_policy_id)
    reward_versions = (
        await db.scalars(select(RewardVersion).where(RewardVersion.id.in_(reward_ids)))
    ).all()
    reward_titles = {str(v.id): reward_opened(v, cipher)["title"] for v in reward_versions}
    return RitualAssignmentView(
        paused_by_id=a.paused_by_id,
        reward_titles=reward_titles,
        reward_version_ids=reward_ids,
        currency_amount=currency,
        reward_policy_id=a.reward_policy_id,
        evidence_policy=EvidencePolicy.model_validate(a.evidence_policy),
        id=a.id,
        ritual_version_id=v.id,
        recipient_id=a.recipient_id,
        issuer_id=a.issuer_id,
        reviewer_ids=await reviewers(db, a),
        approval_required=a.approval_required,
        revision=a.revision,
        status=a.status,
        schedule=Schedule.model_validate(schedule.spec),
        effective=await effective(db, a),
        **opened(v, cipher),
    )


async def occurrence_view(
    db: AsyncSession,
    o: RitualOccurrence,
    a: RitualAssignment,
    uid: UUID,
    now: datetime,
    cipher: PayloadCipher,
) -> OccurrenceView:
    v = await db.get(RitualVersion, a.ritual_version_id)
    assert v is not None
    rows = (
        await db.scalars(
            select(RitualReport)
            .where(RitualReport.occurrence_id == o.id)
            .order_by(RitualReport.attempt)
        )
    ).all()
    reports = []
    for r in rows:
        payload = opened(r, cipher)
        reports.append(
            RitualReportView(
                links=json.loads(payload.get("links", "[]")),
                attachments=[
                    EvidenceView(id=e.id, kind=e.kind, media_type=e.media_type, size=e.size)
                    for e in (
                        await db.scalars(
                            select(RitualEvidence)
                            .options(
                                load_only(
                                    RitualEvidence.id,
                                    RitualEvidence.kind,
                                    RitualEvidence.media_type,
                                    RitualEvidence.size,
                                )
                            )
                            .where(RitualEvidence.report_id == r.id)
                        )
                    ).all()
                ],
                attempt=r.attempt,
                id=r.id,
                text=payload["text"],
                submitted_at=r.submitted_at,
                decision=r.decision,
                reviewer_id=r.reviewer_id,
                reviewed_at=r.reviewed_at,
                comment=payload.get("comment"),
            )
        )
    live = await effective(db, a)
    return OccurrenceView(
        evidence_policy=EvidencePolicy.model_validate(a.evidence_policy),
        id=o.id,
        assignment_id=a.id,
        recipient_id=a.recipient_id,
        local_day=o.local_day,
        due_at=o.due_at,
        expires_at=o.expires_at,
        revision=o.revision,
        status=o.status,
        approval_required=a.approval_required,
        can_report=live
        and uid == a.recipient_id
        and o.status in ("scheduled", "needs_changes")
        and o.due_at <= now < o.expires_at,
        can_review=live and o.status == "submitted" and await can_review(db, a, uid),
        reports=reports,
        **opened(v, cipher),
    )


async def locked(db: AsyncSession, oid: UUID) -> tuple[RitualAssignment, RitualOccurrence]:
    aid = await db.scalar(select(RitualOccurrence.assignment_id).where(RitualOccurrence.id == oid))
    if aid is None:
        raise AppError(404, "NOT_FOUND")
    a = await db.get(RitualAssignment, aid, with_for_update=True)
    o = await db.get(RitualOccurrence, oid, with_for_update=True)
    assert a is not None and o is not None
    return a, o


async def notice(
    db: AsyncSession,
    a: RitualAssignment,
    user_ids: list[UUID],
    kind: str,
    now: datetime,
    o: RitualOccurrence | None = None,
    event: str | None = None,
) -> None:
    for uid in user_ids:
        nid = await db.scalar(
            insert(RitualNotice)
            .values(
                id=uuid4(),
                assignment_id=a.id,
                occurrence_id=o.id if o else None,
                user_id=uid,
                kind=kind,
                created_at=now,
                event_key=event or f"{kind}:{o.id if o else a.id}",
            )
            .on_conflict_do_nothing()
            .returning(RitualNotice.id)
        )
        if nid:
            from vowen.modules.notifications.delivery import enqueue

            await enqueue(
                db, uid, now, ritual_notice_id=nid, occurrence_revision=o.revision if o else None
            )


async def suspend(
    db: AsyncSession, now: datetime, actor_id: UUID | None = None, target_id: UUID | None = None
) -> None:
    """Persist the deny interval even when no worker runs between pause and resume."""
    from datetime import timedelta
    from zoneinfo import ZoneInfo

    from vowen.modules.notifications.delivery import suppress_scope

    await suppress_scope(db, actor_id, target_id)
    query = select(RitualAssignment).where(RitualAssignment.status != "revoked")
    if actor_id is not None and target_id is not None:
        query = query.where(
            RitualAssignment.issuer_id == actor_id, RitualAssignment.recipient_id == target_id
        )
    else:
        uid = actor_id or target_id
        query = query.where(
            (RitualAssignment.issuer_id == uid) | (RitualAssignment.recipient_id == uid)
        )
    rows = (await db.scalars(query.order_by(RitualAssignment.id).with_for_update())).all()
    for a in rows:
        s = await db.get(RitualSchedule, a.current_schedule_id)
        assert s is not None
        today = now.astimezone(ZoneInfo(str(s.spec["timezone"]))).date()
        a.watermark = max(a.watermark, today + timedelta(days=1))
        occurrences = (
            await db.scalars(
                select(RitualOccurrence)
                .where(
                    RitualOccurrence.assignment_id == a.id,
                    RitualOccurrence.status.in_(["scheduled", "needs_changes"]),
                )
                .with_for_update()
            )
        ).all()
        for o in occurrences:
            o.status = "cancelled"
            o.revision += 1


async def transition_assignment(
    db: AsyncSession,
    aid: UUID,
    action: Literal["pause", "resume", "revoke"],
    uid: UUID,
    expected: int,
    now: datetime,
) -> RitualAssignment:
    from vowen.modules.rituals.worker import generate_assignment

    a = await db.get(RitualAssignment, aid, with_for_update=True)
    if a is None:
        raise AppError(404, "NOT_FOUND")
    recipient = a.recipient_id == uid
    if not recipient and (not await can_manage(db, a, uid)):
        raise AppError(403, "ACCESS_DENIED")
    if recipient and action == "pause":
        raise AppError(403, "REQUEST_APPROVAL_REQUIRED")
    if a.revision != expected:
        raise AppError(409, "VERSION_CONFLICT")
    if a.status == "revoked" or (
        action == "resume" and (a.status != "paused" or uid != (a.paused_by_id or a.recipient_id))
    ):
        raise AppError(409, "CONFLICT")
    if action == "resume":
        if not await scoped(db, a.issuer_id, a.recipient_id, "rituals.assign", {a.issuer_id}):
            raise AppError(403, "ACCESS_DENIED")
        await generate_assignment(db, a, now, 31)
        a.status = "active"
        a.paused_by_id = None
    else:
        from vowen.modules.notifications.delivery import suppress_assignment

        await suppress_assignment(db, a.id)
        a.status = "paused" if action == "pause" else "revoked"
        a.paused_by_id = uid if action == "pause" else None
        rows = (
            await db.scalars(
                select(RitualOccurrence)
                .where(
                    RitualOccurrence.assignment_id == aid,
                    RitualOccurrence.status.in_(["scheduled", "needs_changes"]),
                )
                .with_for_update()
            )
        ).all()
        for o in rows:
            o.status = "cancelled"
            o.revision += 1
    a.revision += 1
    await generate_assignment(db, a, now, 31)
    return a
