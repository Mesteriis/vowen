from typing import Literal
from uuid import UUID, uuid4

from fastapi import APIRouter, Request
from sqlalchemy import select

from vowen.core.errors import AppError
from vowen.modules.auth.router import DB, Member
from vowen.modules.forms.service import active
from vowen.modules.relations.router import cipher_for
from vowen.modules.relations.schemas import ExpectedVersion
from vowen.modules.rules import service as rules
from vowen.modules.rules.models import Rule, RuleAssignment, RuleManager, RuleVersion
from vowen.modules.rules.schemas import (
    RuleAssign,
    RuleAssignmentView,
    RuleContent,
    RuleDecision,
    RuleEdit,
    RuleView,
)

router = APIRouter(prefix="/api/v1")


@router.post("/rules", response_model=RuleView)
async def create(body: RuleContent, principal: Member, db: DB, request: Request) -> RuleView:
    await active(db, principal.user_id)
    rule = Rule(id=uuid4(), author_id=principal.user_id)
    db.add(rule)
    await db.flush()
    await rules.new_version(db, rule, body, cipher_for(request))
    return await rules.view(db, rule, cipher_for(request))


@router.get("/rules", response_model=list[RuleView])
async def listing(principal: Member, db: DB, request: Request) -> list[RuleView]:
    rows = (
        await db.scalars(select(Rule).where(Rule.author_id == principal.user_id).order_by(Rule.id))
    ).all()
    return [await rules.view(db, row, cipher_for(request)) for row in rows]


@router.get("/rules/{rid}/versions", response_model=list[RuleView])
async def history(rid: UUID, principal: Member, db: DB, request: Request) -> list[RuleView]:
    rule = await rules.owned(db, rid, principal.user_id)
    versions = (
        await db.scalars(
            select(RuleVersion).where(RuleVersion.rule_id == rid).order_by(RuleVersion.id)
        )
    ).all()
    return [
        RuleView.model_validate(
            dict(
                id=rule.id,
                author_id=rule.author_id,
                revision=rule.revision,
                version_id=v.id,
                status=v.status,
                **rules.content(v, cipher_for(request)).model_dump(),
            )
        )
        for v in versions
    ]


async def change(
    rid: UUID, body: RuleEdit, principal: Member, db: DB, request: Request, fresh: bool
) -> RuleView:
    await active(db, principal.user_id)
    rule = await rules.owned(db, rid, principal.user_id, body.expected_version)
    version = await db.get(RuleVersion, rule.current_version_id)
    assert version is not None
    if fresh:
        if version.status == "draft":
            raise AppError(409, "UNPUBLISHED_VERSION")
        await rules.new_version(
            db,
            rule,
            RuleContent(
                title=body.title,
                description=body.description,
                discipline=body.discipline
                if "discipline" in body.model_fields_set
                else rules.content(version, cipher_for(request)).discipline,
            ),
            cipher_for(request),
        )
    else:
        if version.status != "draft":
            raise AppError(409, "IMMUTABLE_VERSION")
        rules.seal(
            version,
            RuleContent(
                title=body.title,
                description=body.description,
                discipline=body.discipline
                if "discipline" in body.model_fields_set
                else rules.content(version, cipher_for(request)).discipline,
            ),
            cipher_for(request),
        )
    rule.revision += 1
    return await rules.view(db, rule, cipher_for(request))


@router.patch("/rules/{rid}", response_model=RuleView)
async def edit(rid: UUID, body: RuleEdit, principal: Member, db: DB, request: Request) -> RuleView:
    return await change(rid, body, principal, db, request, False)


@router.post("/rules/{rid}/versions", response_model=RuleView)
async def version(
    rid: UUID, body: RuleEdit, principal: Member, db: DB, request: Request
) -> RuleView:
    return await change(rid, body, principal, db, request, True)


@router.post("/rules/{rid}/publish", response_model=RuleView)
async def publish(
    rid: UUID, body: ExpectedVersion, principal: Member, db: DB, request: Request
) -> RuleView:
    await active(db, principal.user_id)
    rule = await rules.owned(db, rid, principal.user_id, body.expected_version)
    version = await db.get(RuleVersion, rule.current_version_id)
    assert version is not None
    if version.status != "draft":
        raise AppError(409, "CONFLICT")
    version.status = "published"
    rule.revision += 1
    return await rules.view(db, rule, cipher_for(request))


@router.post("/rules/{rid}/archive", response_model=RuleView)
async def archive(
    rid: UUID, body: ExpectedVersion, principal: Member, db: DB, request: Request
) -> RuleView:
    rule = await rules.owned(db, rid, principal.user_id, body.expected_version)
    version = await db.get(RuleVersion, rule.current_version_id)
    assert version is not None
    if version.status == "archived":
        raise AppError(409, "CONFLICT")
    version.status = "archived"
    rule.revision += 1
    return await rules.view(db, rule, cipher_for(request))


@router.post("/rules/{rid}/assignments", response_model=RuleAssignmentView)
async def assign(
    rid: UUID, body: RuleAssign, principal: Member, db: DB, request: Request
) -> RuleAssignmentView:
    rule = await rules.owned(db, rid, principal.user_id)
    version = await db.get(RuleVersion, body.rule_version_id)
    if version is None or version.rule_id != rule.id or version.status != "published":
        raise AppError(409, "UNPUBLISHED_VERSION")
    if not await rules.permitted(db, principal.user_id, body.recipient_id, {principal.user_id}):
        raise AppError(403, "ACCESS_DENIED")
    for uid in body.manager_ids:
        if not await rules.permitted(db, uid, body.recipient_id, {uid}):
            raise AppError(403, "ACCESS_DENIED")
    existing = await db.scalar(
        select(RuleAssignment.id).where(
            RuleAssignment.rule_version_id == version.id,
            RuleAssignment.recipient_id == body.recipient_id,
        )
    )
    if existing is not None:
        raise AppError(409, "ALREADY_ASSIGNED")
    assignment = RuleAssignment(
        id=uuid4(),
        rule_id=rule.id,
        rule_version_id=version.id,
        recipient_id=body.recipient_id,
        issuer_id=principal.user_id,
    )
    db.add(assignment)
    await db.flush()
    db.add_all([RuleManager(assignment_id=assignment.id, user_id=uid) for uid in body.manager_ids])
    await db.flush()
    return await rules.assignment_view(db, assignment, cipher_for(request))


@router.get("/rule-assignments", response_model=list[RuleAssignmentView])
async def assignments(principal: Member, db: DB, request: Request) -> list[RuleAssignmentView]:
    rows = (
        await db.scalars(
            select(RuleAssignment)
            .where(
                (RuleAssignment.recipient_id == principal.user_id)
                | RuleAssignment.id.in_(
                    select(RuleManager.assignment_id).where(
                        RuleManager.user_id == principal.user_id
                    )
                )
            )
            .order_by(RuleAssignment.id)
        )
    ).all()
    return [
        await rules.assignment_view(db, row, cipher_for(request))
        for row in rows
        if await rules.visible(db, row, principal.user_id)
    ]


@router.post("/rule-assignments/{aid}/{action}", response_model=RuleAssignmentView)
async def decide(
    aid: UUID,
    action: Literal["accept", "decline", "pause", "revoke"],
    body: RuleDecision,
    principal: Member,
    db: DB,
    request: Request,
) -> RuleAssignmentView:
    assignment = await rules.assignment_locked(db, aid, principal.user_id)
    if (
        assignment.revision != body.expected_version
        or assignment.rule_version_id != body.rule_version_id
    ):
        raise AppError(409, "VERSION_CONFLICT")
    recipient = principal.user_id == assignment.recipient_id
    if action in ("accept", "decline") and not recipient:
        raise AppError(403, "ACCESS_DENIED")
    if action in ("accept", "decline") and assignment.status != "pending_acceptance":
        raise AppError(409, "CONFLICT")
    if action == "accept":
        version = await db.get(RuleVersion, assignment.rule_version_id)
        assert version is not None
        if version.status != "published":
            raise AppError(409, "UNPUBLISHED_VERSION")
        if not await rules.permitted(
            db, assignment.issuer_id, assignment.recipient_id, {assignment.issuer_id}
        ):
            raise AppError(403, "ACCESS_DENIED")
        previous = (
            await db.scalars(
                select(RuleAssignment)
                .where(
                    RuleAssignment.rule_id == assignment.rule_id,
                    RuleAssignment.recipient_id == assignment.recipient_id,
                    RuleAssignment.status == "active",
                )
                .with_for_update()
            )
        ).all()
        for old in previous:
            old.status = "revoked"
            old.decided_at = request.app.state.clock.now()
            old.revision += 1
        await db.flush()
        assignment.status = "active"
        assignment.accepted_at = request.app.state.clock.now()
    elif action == "pause":
        if assignment.status not in ("pending_acceptance", "active"):
            raise AppError(409, "CONFLICT")
        assignment.status = "paused"
    else:
        if assignment.status == "revoked":
            raise AppError(409, "CONFLICT")
        assignment.status = "revoked"
    assignment.decided_at = request.app.state.clock.now()
    assignment.revision += 1
    return await rules.assignment_view(db, assignment, cipher_for(request))
