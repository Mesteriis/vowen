import json
from typing import Literal, cast
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from vowen.core.crypto import EncryptedEnvelope, PayloadCipher
from vowen.core.errors import AppError
from vowen.modules.identity.models import User
from vowen.modules.journal.models import JournalEntry, JournalReader
from vowen.modules.journal.schemas import JournalContent, JournalView


async def readers(db: AsyncSession, e: JournalEntry) -> list[UUID]:
    return list(
        await db.scalars(
            select(JournalReader.user_id)
            .where(JournalReader.entry_id == e.id)
            .order_by(JournalReader.user_id)
        )
    )


async def visible(db: AsyncSession, e: JournalEntry, uid: UUID) -> bool:
    if e.author_id == uid:
        return True
    if not e.published or e.visibility == "private":
        return False
    users = (await db.scalars(select(User).where(User.id.in_([uid, e.author_id])))).all()
    return (
        len(users) == 2
        and all(u.is_active and not u.paused for u in users)
        and uid in await readers(db, e)
    )


async def loaded(db: AsyncSession, eid: UUID, uid: UUID) -> JournalEntry:
    e = await db.get(JournalEntry, eid, with_for_update=True)
    if e is None or not await visible(db, e, uid):
        raise AppError(404, "NOT_FOUND")
    return e


async def audience(
    db: AsyncSession, e: JournalEntry, body: JournalContent, refresh: bool = False
) -> None:
    if body.visibility == "private":
        ids = []
    elif body.visibility == "all_current_members":
        if e.visibility == body.visibility and not refresh:
            return
        ids = list(
            await db.scalars(
                select(User.id)
                .where(User.is_active, ~User.paused, User.id != e.author_id)
                .order_by(User.id)
                .with_for_update()
            )
        )
    else:
        ids = body.reader_ids
        if e.author_id in ids:
            raise AppError(422, "INVALID_INPUT")
        added = set(ids) - set(await readers(db, e))
        found = list(
            await db.scalars(
                select(User.id)
                .where(User.id.in_(added), User.is_active, ~User.paused)
                .order_by(User.id)
                .with_for_update()
            )
        )
        if set(found) != added:
            raise AppError(422, "INVALID_READER")
    await db.execute(delete(JournalReader).where(JournalReader.entry_id == e.id))
    db.add_all([JournalReader(entry_id=e.id, user_id=uid) for uid in ids])
    await db.flush()


def seal(e: JournalEntry, body: JournalContent, cipher: PayloadCipher) -> None:
    payload = body.model_dump_json(include={"date", "title", "text", "mood", "tags"})
    envelope = cipher.seal_payload("journal_entry", e.id, 1, payload.encode())
    e.key_id, e.nonce, e.ciphertext = envelope.key_id, envelope.nonce, envelope.ciphertext
    e.visibility, e.published = body.visibility, body.published


async def view(db: AsyncSession, e: JournalEntry, cipher: PayloadCipher) -> JournalView:
    payload = json.loads(
        cipher.open_payload(
            "journal_entry", e.id, 1, EncryptedEnvelope(e.key_id, e.nonce, e.ciphertext)
        )
    )
    return JournalView(
        id=e.id,
        author_id=e.author_id,
        revision=e.revision,
        created_at=e.created_at,
        updated_at=e.updated_at,
        visibility=cast("Literal['private','selected','all_current_members']", e.visibility),
        reader_ids=await readers(db, e),
        published=e.published,
        **payload,
    )
