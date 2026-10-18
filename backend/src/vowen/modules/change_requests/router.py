import hashlib
import json
from datetime import datetime
from typing import Literal
from uuid import UUID, uuid4

from fastapi import APIRouter, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from vowen.core.crypto import EncryptedEnvelope
from vowen.core.errors import AppError
from vowen.modules.auth.router import DB, Member
from vowen.modules.change_requests.models import ChangeRequest
from vowen.modules.change_requests.schemas import (
    ChangeRequestCreate,
    ChangeRequestDecision,
    ChangeRequestView,
)
from vowen.modules.identity.models import User
from vowen.modules.relations.models import Consent, Relation, RelationVersion
from vowen.modules.relations.router import cipher_for
from vowen.modules.rituals.models import RitualAssignment, RitualOccurrence, RitualVersion
from vowen.modules.rituals.service import opened, transition_assignment
from vowen.modules.rules import service as rules
from vowen.modules.rules.models import Rule, RuleAssignment, RuleManager, RuleVersion
from vowen.modules.rules.schemas import RuleContent

router = APIRouter(prefix="/api/v1/change-requests")


async def authority(db: AsyncSession, rid: UUID, scope: str, uid: UUID, *, lock: bool) -> Relation:
    r = await db.get(Relation, rid)
    if r is None or uid not in (r.dominant_user_id, r.submissive_user_id):
        raise AppError(404, "NOT_FOUND")
    query = (
        select(User)
        .where(User.id.in_([r.dominant_user_id, r.submissive_user_id]))
        .order_by(User.id)
    )
    if lock:
        query = query.with_for_update().execution_options(populate_existing=True)
    users = (await db.scalars(query)).all()
    if lock:
        r = await db.get(Relation, rid, with_for_update=True, populate_existing=True)
        assert r is not None
    version = await db.get(RelationVersion, r.relation_version_id)
    consents = set(
        await db.scalars(
            select(Consent.user_id).where(Consent.relation_version_id == r.relation_version_id)
        )
    )
    if (
        r.status != "active"
        or version is None
        or scope not in version.scopes
        or len(users) != 2
        or any(not u.is_active or u.paused for u in users)
        or not {r.dominant_user_id, r.submissive_user_id}.issubset(consents)
    ):
        raise AppError(403, "ACCESS_DENIED")
    return r


def scope_for(kind: str) -> str:
    return "rituals.assign" if kind.startswith("ritual_") else "rules.assign"


def payload(row: ChangeRequest, request: Request) -> dict:
    return json.loads(
        cipher_for(request).open_payload(
            "change_request", row.id, 1, EncryptedEnvelope(row.key_id, row.nonce, row.ciphertext)
        )
    )


def seal(row: ChangeRequest, body: dict, request: Request) -> None:
    e = cipher_for(request).seal_payload("change_request", row.id, 1, json.dumps(body).encode())
    row.key_id, row.nonce, row.ciphertext = e.key_id, e.nonce, e.ciphertext


def view(row: ChangeRequest, request: Request) -> ChangeRequestView:
    return ChangeRequestView.model_validate(
        dict(
            id=row.id,
            kind=row.kind,
            requester_id=row.requester_id,
            approver_id=row.approver_id,
            relation_id=row.relation_id,
            relation_version_id=row.relation_version_id,
            assignment_id=row.ritual_assignment_id or row.rule_assignment_id,
            occurrence_id=row.occurrence_id,
            rule_version_id=row.rule_version_id,
            result_assignment_id=row.result_assignment_id,
            status=row.status,
            revision=row.revision,
            created_at=row.created_at,
            decided_at=row.decided_at,
            decision_actor_id=row.decision_actor_id,
            **payload(row, request),
        )
    )


async def can_read(db: AsyncSession, row: ChangeRequest, uid: UUID) -> bool:
    if uid == row.requester_id:
        return True
    if uid != row.approver_id:
        return False
    try:
        await authority(db, row.relation_id, scope_for(row.kind), uid, lock=False)
    except AppError:
        return False
    return True


async def target(
    db: AsyncSession, row: ChangeRequest
) -> tuple[RitualAssignment | RuleAssignment | None, RitualOccurrence | None, Rule | None]:
    a: RitualAssignment | RuleAssignment | None = None
    o, rule = None, None
    if row.ritual_assignment_id:
        a = await db.get(
            RitualAssignment, row.ritual_assignment_id, with_for_update=True, populate_existing=True
        )
        if row.occurrence_id:
            o = await db.get(
                RitualOccurrence, row.occurrence_id, with_for_update=True, populate_existing=True
            )
            if o is None or o.assignment_id != row.ritual_assignment_id:
                raise AppError(404, "NOT_FOUND")
    elif row.rule_assignment_id:
        rid = await db.scalar(
            select(RuleAssignment.rule_id).where(RuleAssignment.id == row.rule_assignment_id)
        )
        if rid:
            rule = await db.get(Rule, rid, with_for_update=True, populate_existing=True)
        a = await db.get(
            RuleAssignment, row.rule_assignment_id, with_for_update=True, populate_existing=True
        )
    if row.kind != "rule_add" and (
        a is None or a.recipient_id != row.requester_id or a.issuer_id != row.approver_id
    ):
        raise AppError(404, "NOT_FOUND")
    return a, o, rule


def validate_target(
    row: ChangeRequest,
    a: RitualAssignment | RuleAssignment | None,
    o: RitualOccurrence | None,
    rule: Rule | None,
    now: datetime,
) -> None:
    if a is None:
        return
    if a.revision != row.assignment_revision:
        raise AppError(409, "VERSION_CONFLICT")
    if row.kind.startswith("ritual_"):
        if a.status != "active" or (
            o is not None
            and (
                o.revision != row.target_revision
                or o.status not in ("scheduled", "needs_changes")
                or now >= o.expires_at
            )
        ):
            raise AppError(409, "VERSION_CONFLICT")
    else:
        assert isinstance(a, RuleAssignment) and rule is not None
        if (
            a.status not in ("active", "paused", "pending_acceptance")
            or a.rule_version_id != row.rule_version_id
            or rule.revision != row.rule_revision
            or rule.author_id != row.approver_id
            or (row.kind == "rule_edit" and rule.current_version_id != row.rule_version_id)
        ):
            raise AppError(409, "VERSION_CONFLICT")


@router.get("", response_model=list[ChangeRequestView])
async def listing(principal: Member, db: DB, request: Request) -> list[ChangeRequestView]:
    rows = (
        await db.scalars(
            select(ChangeRequest)
            .where(
                (ChangeRequest.requester_id == principal.user_id)
                | (ChangeRequest.approver_id == principal.user_id)
            )
            .order_by(ChangeRequest.created_at.desc(), ChangeRequest.id)
        )
    ).all()
    return [view(r, request) for r in rows if await can_read(db, r, principal.user_id)]


@router.post("", response_model=ChangeRequestView)
async def create(
    body: ChangeRequestCreate, principal: Member, db: DB, request: Request
) -> ChangeRequestView:
    digest = hashlib.sha256(body.model_dump_json().encode()).digest()
    old = await db.scalar(
        select(ChangeRequest).where(
            ChangeRequest.requester_id == principal.user_id,
            ChangeRequest.idempotency_key == body.idempotency_key,
        )
    )
    if old is not None:
        if old.request_hash != digest:
            raise AppError(409, "IDEMPOTENCY_CONFLICT")
        return view(old, request)
    assignment: RitualAssignment | RuleAssignment | None = None
    if body.kind != "rule_add":
        assignment = await db.get(
            RitualAssignment if body.kind.startswith("ritual_") else RuleAssignment,
            body.assignment_id,
        )
        if assignment is None or assignment.recipient_id != principal.user_id:
            raise AppError(404, "NOT_FOUND")
        rid = await db.scalar(
            select(Relation.id).where(
                Relation.dominant_user_id == assignment.issuer_id,
                Relation.submissive_user_id == principal.user_id,
                Relation.status != "revoked",
            )
        )
    else:
        rid = body.relation_id
    if rid is None or (body.relation_id is not None and body.relation_id != rid):
        raise AppError(404, "NOT_FOUND")
    r = await authority(db, rid, scope_for(body.kind), principal.user_id, lock=True)
    if r.submissive_user_id != principal.user_id:
        raise AppError(404, "NOT_FOUND")
    # Party locks serialize retries across targets without reversing the relation lock order.
    old = await db.scalar(
        select(ChangeRequest).where(
            ChangeRequest.requester_id == principal.user_id,
            ChangeRequest.idempotency_key == body.idempotency_key,
        )
    )
    if old is not None:
        if old.request_hash != digest:
            raise AppError(409, "IDEMPOTENCY_CONFLICT")
        return view(old, request)
    row = ChangeRequest(
        id=uuid4(),
        kind=body.kind,
        requester_id=principal.user_id,
        approver_id=r.dominant_user_id,
        relation_id=r.id,
        relation_version_id=r.relation_version_id,
        ritual_assignment_id=body.assignment_id if body.kind.startswith("ritual_") else None,
        rule_assignment_id=body.assignment_id
        if body.kind in ("rule_edit", "rule_delete")
        else None,
        occurrence_id=body.occurrence_id,
        target_revision=body.expected_version,
        idempotency_key=body.idempotency_key,
        request_hash=digest,
        created_at=request.app.state.clock.now(),
    )
    a, o, rule = await target(db, row)
    row.assignment_revision = a.revision if a else None
    row.rule_revision = rule.revision if rule else None
    row.rule_version_id = a.rule_version_id if isinstance(a, RuleAssignment) else None
    if a is not None and (o.revision if o else a.revision) != body.expected_version:
        raise AppError(409, "VERSION_CONFLICT")
    validate_target(row, a, o, rule, request.app.state.clock.now())
    if body.kind != "rule_add":
        pending = await db.scalar(
            select(ChangeRequest.id).where(
                ChangeRequest.status == "pending",
                ChangeRequest.requester_id == principal.user_id,
                ChangeRequest.ritual_assignment_id == row.ritual_assignment_id,
                ChangeRequest.rule_assignment_id == row.rule_assignment_id,
                ChangeRequest.occurrence_id == row.occurrence_id,
            )
        )
        if pending:
            raise AppError(409, "REQUEST_PENDING")
    title = body.content.title if body.content else ""
    if isinstance(a, RitualAssignment):
        version = await db.get(RitualVersion, a.ritual_version_id)
        assert version is not None
        title = opened(version, cipher_for(request))["title"]
    elif isinstance(a, RuleAssignment):
        version_rule = await db.get(RuleVersion, a.rule_version_id)
        assert version_rule is not None
        title = rules.content(version_rule, cipher_for(request)).title
    seal(
        row,
        dict(
            title=title,
            reason=body.reason,
            content=body.content.model_dump() if body.content else None,
            comment="",
        ),
        request,
    )
    db.add(row)
    await db.flush()
    return view(row, request)


@router.post("/{qid}/{action}", response_model=ChangeRequestView)
async def decide(
    qid: UUID,
    action: Literal["approve", "reject", "withdraw"],
    body: ChangeRequestDecision,
    principal: Member,
    db: DB,
    request: Request,
) -> ChangeRequestView:
    row = await db.get(ChangeRequest, qid)
    uid = principal.user_id
    if row is None or uid != (row.requester_id if action == "withdraw" else row.approver_id):
        raise AppError(404, "NOT_FOUND")
    r = None
    if action != "withdraw":
        r = await authority(db, row.relation_id, scope_for(row.kind), uid, lock=True)
    # Always lock domain targets before the proposal; consistent with direct mutations.
    a, o, rule = await target(db, row)
    row = await db.get(ChangeRequest, qid, with_for_update=True, populate_existing=True)
    assert row is not None
    wanted = {"approve": "approved", "reject": "rejected", "withdraw": "withdrawn"}[action]
    p = payload(row, request)
    if row.status != "pending":
        if row.status == wanted and row.decision_actor_id == uid and p["comment"] == body.comment:
            return view(row, request)
        raise AppError(409, "REQUEST_DECIDED")
    if row.revision != body.expected_version:
        raise AppError(409, "VERSION_CONFLICT")
    if action == "approve":
        assert r is not None
        if r.relation_version_id != row.relation_version_id:
            raise AppError(409, "AGREEMENT_CHANGED")
        validate_target(row, a, o, rule, request.app.state.clock.now())
        if row.kind == "ritual_skip":
            assert o is not None
            from vowen.modules.notifications.delivery import cancel_where
            from vowen.modules.notifications.models import MemberDelivery
            from vowen.modules.rituals.models import RitualNotice

            await cancel_where(
                db,
                MemberDelivery.ritual_notice_id.in_(
                    select(RitualNotice.id).where(RitualNotice.occurrence_id == o.id)
                ),
            )
            o.status, o.revision = "skipped", o.revision + 1
        elif row.kind == "ritual_pause":
            assert isinstance(a, RitualAssignment)
            await transition_assignment(
                db, a.id, "pause", uid, a.revision, request.app.state.clock.now()
            )
        elif row.kind == "rule_delete":
            assert isinstance(a, RuleAssignment)
            a.status, a.revision, a.decided_at = (
                "revoked",
                a.revision + 1,
                request.app.state.clock.now(),
            )
        else:
            if row.kind == "rule_add":
                rule = Rule(id=uuid4(), author_id=uid)
                db.add(rule)
                await db.flush()
            assert rule is not None
            if row.kind == "rule_edit":
                version = await db.get(RuleVersion, rule.current_version_id)
                if version is None or version.status != "published":
                    raise AppError(409, "VERSION_CONFLICT")
            await rules.new_version(
                db, rule, RuleContent.model_validate(p["content"]), cipher_for(request)
            )
            version = await db.get(RuleVersion, rule.current_version_id)
            assert version is not None
            version.status = "published"
            rule.revision += 1
            replacement = RuleAssignment(
                id=uuid4(),
                rule_id=rule.id,
                rule_version_id=version.id,
                recipient_id=row.requester_id,
                issuer_id=uid,
            )
            db.add(replacement)
            await db.flush()
            manager_ids = (
                set(await rules.managers(db, a)) if isinstance(a, RuleAssignment) else set()
            )
            manager_ids.add(uid)
            for manager_id in sorted(manager_ids):
                if not await rules.permitted(db, manager_id, row.requester_id, {manager_id}):
                    raise AppError(403, "ACCESS_DENIED")
                db.add(RuleManager(assignment_id=replacement.id, user_id=manager_id))
            row.result_assignment_id = replacement.id
    row.status, row.revision = wanted, row.revision + 1
    row.decided_at, row.decision_actor_id = request.app.state.clock.now(), uid
    p["comment"] = body.comment
    seal(row, p, request)
    await db.flush()
    return view(row, request)
