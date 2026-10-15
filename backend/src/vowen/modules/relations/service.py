from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from vowen.core.crypto import EncryptedEnvelope, PayloadCipher
from vowen.core.errors import AppError
from vowen.modules.auth.service import MemberPrincipal, OperatorContext
from vowen.modules.identity.models import User
from vowen.modules.relations.models import Consent, Relation, RelationVersion
from vowen.modules.relations.schemas import ProposeRelationCommand, RelationView, VersionContent


async def new_version(
    db: AsyncSession, relation: Relation, content: VersionContent, cipher: PayloadCipher
) -> None:
    version_id = uuid4()
    sealed = cipher.seal_payload("agreement", version_id, 1, content.agreement_text.encode())
    db.add(
        RelationVersion(
            id=version_id,
            relation_id=relation.id,
            scopes=list(content.scopes),
            key_id=sealed.key_id,
            nonce=sealed.nonce,
            ciphertext=sealed.ciphertext,
        )
    )
    await db.flush()
    relation.relation_version_id = version_id
    relation.status = "proposed"


async def propose_relation(
    db: AsyncSession,
    actor: MemberPrincipal | OperatorContext,
    command: ProposeRelationCommand,
    cipher: PayloadCipher,
) -> Relation:
    if command.dominant_user_id == command.submissive_user_id:
        raise AppError(422, "INVALID_INPUT")
    if isinstance(actor, MemberPrincipal):
        if actor.user_id not in (command.dominant_user_id, command.submissive_user_id):
            raise AppError(403, "ACCESS_DENIED")
    elif not isinstance(actor, OperatorContext):
        raise AppError(403, "ACCESS_DENIED")
    # Deterministic user lock order shared by relation commands and disable.
    users = (
        await db.scalars(
            select(User)
            .where(User.id.in_([command.dominant_user_id, command.submissive_user_id]))
            .order_by(User.id)
            .with_for_update()
        )
    ).all()
    if len(users) != 2 or any(not user.is_active or user.paused for user in users):
        raise AppError(403, "ACCESS_DENIED")
    relation = Relation(
        dominant_user_id=command.dominant_user_id, submissive_user_id=command.submissive_user_id
    )
    try:
        async with db.begin_nested():
            db.add(relation)
            await db.flush()
            await new_version(db, relation, command, cipher)
    except IntegrityError:
        raise AppError(409, "CONFLICT") from None
    return relation


async def owned_relation(
    db: AsyncSession, actor: MemberPrincipal, relation_id: UUID, expected_version: int | None = None
) -> Relation:
    if not isinstance(actor, MemberPrincipal):
        raise AppError(403, "ACCESS_DENIED")
    relation = await db.scalar(
        select(Relation)
        .where(
            Relation.id == relation_id,
            (Relation.dominant_user_id == actor.user_id)
            | (Relation.submissive_user_id == actor.user_id),
        )
        .with_for_update()
    )
    if relation is None:
        raise AppError(404, "NOT_FOUND")
    if expected_version is not None and relation.version != expected_version:
        raise AppError(409, "CONFLICT")
    return relation


async def accept_relation(
    db: AsyncSession,
    actor: MemberPrincipal,
    relation: Relation,
    relation_version_id: UUID,
    now: datetime,
) -> None:
    if not isinstance(actor, MemberPrincipal) or actor.user_id not in (
        relation.dominant_user_id,
        relation.submissive_user_id,
    ):
        raise AppError(403, "ACCESS_DENIED")
    if relation.status != "proposed" or relation.relation_version_id != relation_version_id:
        raise AppError(409, "CONFLICT")
    users = (
        await db.scalars(
            select(User).where(
                User.id.in_([relation.dominant_user_id, relation.submissive_user_id])
            )
        )
    ).all()
    if any(not u.is_active or u.paused for u in users):
        raise AppError(403, "ACCESS_DENIED")
    if await db.get(Consent, (relation_version_id, actor.user_id)) is not None:
        raise AppError(409, "CONFLICT")
    db.add(Consent(relation_version_id=relation_version_id, user_id=actor.user_id, accepted_at=now))
    await db.flush()
    consents = (
        await db.scalars(
            select(Consent.user_id).where(Consent.relation_version_id == relation_version_id)
        )
    ).all()
    if set(consents) == {relation.dominant_user_id, relation.submissive_user_id}:
        relation.status = "active"
    relation.version += 1


async def view_relation(
    db: AsyncSession, relation: Relation, cipher: PayloadCipher
) -> RelationView:
    version = await db.get(RelationVersion, relation.relation_version_id)
    assert version is not None
    text = cipher.open_payload(
        "agreement",
        version.id,
        1,
        EncryptedEnvelope(version.key_id, version.nonce, version.ciphertext),
    ).decode()
    consents = list(
        (
            await db.scalars(
                select(Consent.user_id).where(Consent.relation_version_id == version.id)
            )
        ).all()
    )
    return RelationView(
        id=relation.id,
        dominant_user_id=relation.dominant_user_id,
        submissive_user_id=relation.submissive_user_id,
        status=relation.status,
        version=relation.version,
        relation_version_id=version.id,
        scopes=version.scopes,
        agreement_text=text,
        consent_user_ids=consents,
    )
