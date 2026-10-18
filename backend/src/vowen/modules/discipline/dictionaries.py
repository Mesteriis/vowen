"""Explicit dictionaries belonging to a directly consented relationship."""

from hashlib import sha256
from typing import Literal
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from vowen.core.crypto import EncryptedEnvelope, PayloadCipher
from vowen.core.errors import AppError
from vowen.modules.discipline.models import DisciplineDictionary
from vowen.modules.discipline.service import lock_authority, permitted
from vowen.modules.references.models import BodyPart, Device
from vowen.modules.relations.models import Relation

Kind = Literal["device", "body_part"]


async def relationship(db: AsyncSession, rid: UUID, uid: UUID, *, write: bool = False) -> Relation:
    row = await db.get(Relation, rid, with_for_update=write)
    if row is None or uid not in {row.dominant_user_id, row.submissive_user_id}:
        raise AppError(404, "NOT_FOUND")
    await lock_authority(db, row.submissive_user_id, [row.dominant_user_id])
    if write and uid != row.dominant_user_id:
        raise AppError(403, "ACCESS_DENIED")
    if not await permitted(db, row.dominant_user_id, row.submissive_user_id, "discipline.propose"):
        raise AppError(403, "ACCESS_DENIED")
    return row


async def values(db: AsyncSession, rid: UUID, kind: Kind, cipher: PayloadCipher) -> list[str]:
    rows = (
        await db.scalars(
            select(DisciplineDictionary)
            .where(DisciplineDictionary.relation_id == rid, DisciplineDictionary.kind == kind)
            .order_by(DisciplineDictionary.id)
        )
    ).all()
    model = Device if kind == "device" else BodyPart
    shared = list(
        await db.scalars(
            select(model.name)
            .where(model.extra["discipline_default"].as_boolean().is_(True))
            .order_by(model.name, model.uid)
        )
    )
    private = [
        cipher.open_payload(
            "discipline_dictionary",
            row.id,
            1,
            EncryptedEnvelope(row.key_id, row.nonce, row.ciphertext),
        ).decode()
        for row in rows
    ]
    # Private additions stay relationship-scoped; duplicate labels are displayed once.
    result: list[str] = []
    seen: set[str] = set()
    for value in shared + private:
        if value.casefold() not in seen:
            result.append(value)
            seen.add(value.casefold())
    return result


async def add(
    db: AsyncSession, rid: UUID, kind: Kind, name: str, cipher: PayloadCipher
) -> list[str]:
    existing = await values(db, rid, kind, cipher)
    if name.casefold() not in {value.casefold() for value in existing}:
        row = DisciplineDictionary(
            id=uuid4(),
            relation_id=rid,
            kind=kind,
            name_digest=sha256(name.casefold().encode()).hexdigest(),
        )
        envelope = cipher.seal_payload("discipline_dictionary", row.id, 1, name.encode())
        row.key_id, row.nonce, row.ciphertext = envelope.key_id, envelope.nonce, envelope.ciphertext
        db.add(row)
        await db.flush()
    return await values(db, rid, kind, cipher)
