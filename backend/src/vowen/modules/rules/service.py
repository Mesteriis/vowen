import json
from typing import Literal, cast
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from vowen.core.crypto import EncryptedEnvelope, PayloadCipher
from vowen.core.errors import AppError
from vowen.modules.auth.service import MemberPrincipal
from vowen.modules.relations.policy import ResourceContext, authorize
from vowen.modules.rules.models import Rule, RuleAssignment, RuleManager, RuleVersion
from vowen.modules.rules.schemas import RuleAssignmentView, RuleContent, RuleView


def seal(version: RuleVersion, content: RuleContent, cipher: PayloadCipher) -> None:
    envelope = cipher.seal_payload(
        "rule_version", version.id, 1, content.model_dump_json().encode()
    )
    version.key_id, version.nonce, version.ciphertext = (
        envelope.key_id,
        envelope.nonce,
        envelope.ciphertext,
    )


def content(version: RuleVersion, cipher: PayloadCipher) -> RuleContent:
    return RuleContent.model_validate(
        json.loads(
            cipher.open_payload(
                "rule_version",
                version.id,
                1,
                EncryptedEnvelope(version.key_id, version.nonce, version.ciphertext),
            )
        )
    )


async def new_version(
    db: AsyncSession, rule: Rule, body: RuleContent, cipher: PayloadCipher
) -> None:
    version = RuleVersion(id=uuid4(), rule_id=rule.id)
    seal(version, body, cipher)
    db.add(version)
    await db.flush()
    rule.current_version_id = version.id


async def owned(db: AsyncSession, rid: UUID, uid: UUID, expected: int | None = None) -> Rule:
    rule = await db.get(Rule, rid, with_for_update=True)
    if rule is None or rule.author_id != uid:
        raise AppError(404, "NOT_FOUND")
    if expected is not None and rule.revision != expected:
        raise AppError(409, "VERSION_CONFLICT")
    return rule


async def view(db: AsyncSession, rule: Rule, cipher: PayloadCipher) -> RuleView:
    version = await db.get(RuleVersion, rule.current_version_id)
    assert version is not None
    return RuleView(
        id=rule.id,
        author_id=rule.author_id,
        revision=rule.revision,
        version_id=version.id,
        status=cast("LiteralStatus", version.status),
        **content(version, cipher).model_dump(),
    )


# Keep database strings validated at the response boundary.

LiteralStatus = Literal["draft", "published", "archived"]


async def permitted(db: AsyncSession, uid: UUID, target: UUID, actors: set[UUID]) -> bool:
    try:
        await authorize(
            db,
            MemberPrincipal(uid, UUID(int=0)),
            "rules.assign",
            ResourceContext(target, frozenset(actors)),
        )
    except AppError:
        return False
    return True


async def managers(db: AsyncSession, assignment: RuleAssignment) -> list[UUID]:
    return list(
        await db.scalars(
            select(RuleManager.user_id)
            .where(RuleManager.assignment_id == assignment.id)
            .order_by(RuleManager.user_id)
        )
    )


async def visible(db: AsyncSession, assignment: RuleAssignment, uid: UUID) -> bool:
    return assignment.recipient_id == uid or await permitted(
        db, uid, assignment.recipient_id, set(await managers(db, assignment))
    )


async def assignment_view(
    db: AsyncSession, assignment: RuleAssignment, cipher: PayloadCipher
) -> RuleAssignmentView:
    version = await db.get(RuleVersion, assignment.rule_version_id)
    assert version is not None
    return RuleAssignmentView(
        id=assignment.id,
        rule_id=assignment.rule_id,
        rule_version_id=version.id,
        recipient_id=assignment.recipient_id,
        manager_ids=await managers(db, assignment),
        revision=assignment.revision,
        status=cast(
            "Literal['pending_acceptance', 'active', 'paused', 'revoked']", assignment.status
        ),
        accepted_at=assignment.accepted_at,
        decided_at=assignment.decided_at,
        effective=assignment.status == "active"
        and await permitted(
            db, assignment.issuer_id, assignment.recipient_id, {assignment.issuer_id}
        ),
        **content(version, cipher).model_dump(),
    )


async def assignment_locked(db: AsyncSession, aid: UUID, uid: UUID) -> RuleAssignment:
    # All mutations take the template lock first, including replacement acceptance.
    rid = await db.scalar(select(RuleAssignment.rule_id).where(RuleAssignment.id == aid))
    if rid is None:
        raise AppError(404, "NOT_FOUND")
    await db.get(Rule, rid, with_for_update=True)
    assignment = await db.get(RuleAssignment, aid, with_for_update=True)
    assert assignment is not None
    if not await visible(db, assignment, uid):
        raise AppError(404, "NOT_FOUND")
    return assignment
