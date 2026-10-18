"""Reusable relationship templates and explicit per-assignment parameters."""

from uuid import UUID, uuid4

from fastapi import APIRouter, Request
from sqlalchemy import select

from vowen.core.crypto import EncryptedEnvelope, PayloadCipher
from vowen.core.errors import AppError
from vowen.modules.auth.router import DB, Member
from vowen.modules.discipline import dictionaries, service
from vowen.modules.discipline.models import PunishmentTemplate
from vowen.modules.discipline.schemas import (
    DisciplineCreate,
    DisciplineView,
    PunishmentAssign,
    PunishmentTemplateContent,
    PunishmentTemplateCreate,
    PunishmentTemplateEdit,
    PunishmentTemplateView,
)
from vowen.modules.relations.router import cipher_for
from vowen.modules.relations.schemas import ExpectedVersion

router = APIRouter(prefix="/api/v1/punishment-templates")


def content(row: PunishmentTemplate, cipher: PayloadCipher) -> PunishmentTemplateContent:
    return PunishmentTemplateContent.model_validate_json(
        cipher.open_payload(
            "punishment_template",
            row.id,
            1,
            EncryptedEnvelope(row.key_id, row.nonce, row.ciphertext),
        )
    )


def seal(row: PunishmentTemplate, body: PunishmentTemplateContent, cipher: PayloadCipher) -> None:
    value = cipher.seal_payload("punishment_template", row.id, 1, body.model_dump_json().encode())
    row.key_id, row.nonce, row.ciphertext = value.key_id, value.nonce, value.ciphertext


def view(row: PunishmentTemplate, cipher: PayloadCipher, edit: bool) -> PunishmentTemplateView:
    return PunishmentTemplateView(
        id=row.id,
        relation_id=row.relation_id,
        revision=row.revision,
        can_edit=edit,
        **content(row, cipher).model_dump(),
    )


async def validate_dictionary(
    db: DB, rid: UUID, body: PunishmentTemplateContent, cipher: PayloadCipher
) -> None:
    if body.punishment_type == "physical":
        choices: list[tuple[dictionaries.Kind, str | None]] = [
            ("device", body.device),
            ("body_part", body.body_part),
        ]
        for kind, name in choices:
            if name not in await dictionaries.values(db, rid, kind, cipher):
                raise AppError(422, "INVALID_DICTIONARY_VALUE")


@router.get("", response_model=list[PunishmentTemplateView])
async def listing(relation_id: UUID, principal: Member, db: DB, request: Request):
    relation = await dictionaries.relationship(db, relation_id, principal.user_id)
    rows = (
        await db.scalars(
            select(PunishmentTemplate)
            .where(PunishmentTemplate.relation_id == relation_id, ~PunishmentTemplate.archived)
            .order_by(PunishmentTemplate.id)
        )
    ).all()
    return [
        view(row, cipher_for(request), relation.dominant_user_id == principal.user_id)
        for row in rows
    ]


@router.post("", response_model=PunishmentTemplateView)
async def create(body: PunishmentTemplateCreate, principal: Member, db: DB, request: Request):
    await dictionaries.relationship(db, body.relation_id, principal.user_id, write=True)
    value = PunishmentTemplateContent.model_validate(body.model_dump(exclude={"relation_id"}))
    await validate_dictionary(db, body.relation_id, value, cipher_for(request))
    row = PunishmentTemplate(id=uuid4(), relation_id=body.relation_id, revision=1, archived=False)
    seal(row, value, cipher_for(request))
    db.add(row)
    await db.flush()
    return view(row, cipher_for(request), True)


async def locked(tid: UUID, uid: UUID, db: DB) -> PunishmentTemplate:
    # Relation lock first, same order as catalogue creation and assignment.
    row = await db.get(PunishmentTemplate, tid)
    if row is None or row.archived:
        raise AppError(404, "NOT_FOUND")
    await dictionaries.relationship(db, row.relation_id, uid, write=True)
    row = await db.get(PunishmentTemplate, tid, with_for_update=True, populate_existing=True)
    if row is None or row.archived:
        raise AppError(404, "NOT_FOUND")
    return row


@router.patch("/{tid}", response_model=PunishmentTemplateView)
async def edit(
    tid: UUID, body: PunishmentTemplateEdit, principal: Member, db: DB, request: Request
):
    row = await locked(tid, principal.user_id, db)
    if row.revision != body.expected_version:
        raise AppError(409, "VERSION_CONFLICT")
    value = PunishmentTemplateContent.model_validate(body.model_dump(exclude={"expected_version"}))
    await validate_dictionary(db, row.relation_id, value, cipher_for(request))
    seal(row, value, cipher_for(request))
    row.revision += 1
    return view(row, cipher_for(request), True)


@router.post("/{tid}/archive", status_code=204)
async def archive(tid: UUID, body: ExpectedVersion, principal: Member, db: DB):
    row = await locked(tid, principal.user_id, db)
    if row.revision != body.expected_version:
        raise AppError(409, "VERSION_CONFLICT")
    row.archived = True
    row.revision += 1


@router.post("/{tid}/assign", response_model=DisciplineView)
async def assign(tid: UUID, body: PunishmentAssign, principal: Member, db: DB, request: Request):
    row = await locked(tid, principal.user_id, db)
    if row.revision != body.expected_version:
        raise AppError(409, "VERSION_CONFLICT")
    relation = await dictionaries.relationship(db, row.relation_id, principal.user_id, write=True)
    value = content(row, cipher_for(request))
    if (value.punishment_type == "physical") != (body.intensity is not None):
        raise AppError(422, "INVALID_INPUT")
    snapshot = DisciplineCreate(
        description=value.description,
        assignment_title=value.title,
        conditions=value.conditions or value.description,
        punishment_type=value.punishment_type,
        device=value.device,
        body_part=value.body_part,
        strike_count=value.strike_count,
        ban_days=value.ban_days,
        intensity=body.intensity,
        assignment_comment=body.comment,
        rule_version_id=body.rule_version_id,
        recipient_id=relation.submissive_user_id,
        reviewer_ids=[principal.user_id],
        idempotency_key=body.idempotency_key,
    )
    return await service.create_record(
        db, principal.user_id, snapshot, cipher_for(request), request.app.state.clock.now()
    )
