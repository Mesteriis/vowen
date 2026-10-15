from uuid import UUID

from fastapi import APIRouter, Request, Response
from sqlalchemy import select

from vowen.core.crypto import PayloadCipher
from vowen.core.errors import AppError
from vowen.modules.auth.router import DB, Member
from vowen.modules.identity.models import User
from vowen.modules.relations.models import Relation
from vowen.modules.relations.schemas import (
    AcceptRelation,
    ChangeVersion,
    ExpectedVersion,
    ProposeRelationCommand,
    RelationView,
    VersionContent,
)
from vowen.modules.relations.service import (
    accept_relation,
    new_version,
    owned_relation,
    propose_relation,
    view_relation,
)
from vowen.modules.rituals.service import suspend

router = APIRouter(prefix="/api/v1")


def cipher_for(request: Request) -> PayloadCipher:
    try:
        return PayloadCipher(request.app.state.settings.data_keyring_file)
    except (OSError, ValueError, KeyError):
        raise AppError(503, "UNAVAILABLE") from None


@router.post("/relations", response_model=RelationView)
async def propose(
    body: ProposeRelationCommand, principal: Member, db: DB, request: Request
) -> RelationView:
    cipher = cipher_for(request)
    relation = await propose_relation(db, principal, body, cipher)
    return await view_relation(db, relation, cipher)


@router.get("/relations", response_model=list[RelationView])
async def listing(principal: Member, db: DB, request: Request) -> list[RelationView]:
    relations = (
        await db.scalars(
            select(Relation).where(
                (Relation.dominant_user_id == principal.user_id)
                | (Relation.submissive_user_id == principal.user_id)
            )
        )
    ).all()
    if not relations:
        return []
    cipher = cipher_for(request)
    return [await view_relation(db, relation, cipher) for relation in relations]


@router.post("/relations/{relation_id}/accept", response_model=RelationView)
async def accept(
    relation_id: UUID, body: AcceptRelation, principal: Member, db: DB, request: Request
) -> RelationView:
    relation = await owned_relation(db, principal, relation_id, body.expected_version)
    await accept_relation(
        db, principal, relation, body.relation_version_id, request.app.state.clock.now()
    )
    if relation.status == "active":
        await suspend(
            db,
            request.app.state.clock.now(),
            relation.dominant_user_id,
            relation.submissive_user_id,
        )
    return await view_relation(db, relation, cipher_for(request))


@router.post("/relations/{relation_id}/pause", response_model=RelationView)
async def pause(
    relation_id: UUID, body: ExpectedVersion, principal: Member, db: DB, request: Request
) -> RelationView:
    relation = await owned_relation(db, principal, relation_id, body.expected_version)
    if relation.status not in ("active", "proposed"):
        raise AppError(409, "CONFLICT")
    await suspend(
        db, request.app.state.clock.now(), relation.dominant_user_id, relation.submissive_user_id
    )
    relation.status = "paused"
    relation.version += 1
    return await view_relation(db, relation, cipher_for(request))


@router.post("/relations/{relation_id}/revoke", response_model=RelationView)
async def revoke(
    relation_id: UUID, body: ExpectedVersion, principal: Member, db: DB, request: Request
) -> RelationView:
    relation = await owned_relation(db, principal, relation_id, body.expected_version)
    if relation.status == "revoked":
        raise AppError(409, "CONFLICT")
    await suspend(
        db, request.app.state.clock.now(), relation.dominant_user_id, relation.submissive_user_id
    )
    relation.status = "revoked"
    relation.version += 1
    return await view_relation(db, relation, cipher_for(request))


@router.post("/relations/{relation_id}/resume", response_model=RelationView)
async def resume(
    relation_id: UUID, body: ExpectedVersion, principal: Member, db: DB, request: Request
) -> RelationView:
    relation = await owned_relation(db, principal, relation_id, body.expected_version)
    if relation.status != "paused":
        raise AppError(409, "CONFLICT")
    cipher = cipher_for(request)
    old = await view_relation(db, relation, cipher)
    content = VersionContent.model_validate(
        {"scopes": old.scopes, "agreement_text": old.agreement_text}
    )
    await new_version(db, relation, content, cipher)
    relation.version += 1
    return await view_relation(db, relation, cipher)


@router.post("/relations/{relation_id}/versions", response_model=RelationView)
async def change(
    relation_id: UUID, body: ChangeVersion, principal: Member, db: DB, request: Request
) -> RelationView:
    relation = await owned_relation(db, principal, relation_id, body.expected_version)
    if relation.status == "revoked":
        raise AppError(409, "CONFLICT")
    cipher = cipher_for(request)
    await suspend(
        db, request.app.state.clock.now(), relation.dominant_user_id, relation.submissive_user_id
    )
    await new_version(db, relation, body, cipher)
    relation.version += 1
    return await view_relation(db, relation, cipher)


@router.post("/me/pause", status_code=204)
async def personal_pause(principal: Member, db: DB, request: Request) -> Response:
    user = await db.get(User, principal.user_id, with_for_update=True)
    assert user is not None
    await suspend(db, request.app.state.clock.now(), target_id=principal.user_id)
    user.paused = True
    return Response(status_code=204)


@router.post("/me/resume", status_code=204)
async def personal_resume(principal: Member, db: DB, request: Request) -> Response:
    user = await db.get(User, principal.user_id, with_for_update=True)
    assert user is not None
    if user.paused:
        await suspend(db, request.app.state.clock.now(), target_id=principal.user_id)
    user.paused = False
    return Response(status_code=204)
