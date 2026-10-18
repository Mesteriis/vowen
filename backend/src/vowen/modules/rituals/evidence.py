"""Bounded private evidence. URLs are inert data; media is never server-decoded."""

import base64
import binascii
import hashlib
import json
from datetime import datetime, timedelta
from urllib.parse import urlsplit
from uuid import UUID, uuid4

from fastapi import APIRouter, Request
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import load_only

from vowen.core.crypto import EncryptedEnvelope
from vowen.core.errors import AppError
from vowen.modules.auth.router import DB, Member
from vowen.modules.identity.models import User
from vowen.modules.relations.router import cipher_for
from vowen.modules.rituals import service
from vowen.modules.rituals.models import RitualAssignment, RitualEvidence, RitualOccurrence
from vowen.modules.rituals.schemas import (
    EvidenceDownload,
    EvidencePolicy,
    EvidenceUpload,
    EvidenceView,
    ReportCommand,
)

router = APIRouter(prefix="/api/v1")


def report_payload(body: ReportCommand) -> dict[str, str]:
    return {
        "text": body.text,
        "links": json.dumps(body.links),
        "evidence_ids": json.dumps(sorted(str(i) for i in body.evidence_ids)),
    }


def validate_links(links: list[str]) -> None:
    for link in links:
        try:
            u = urlsplit(link)
            valid = (
                len(link) <= 2048
                and u.scheme == "https"
                and bool(u.hostname)
                and not u.username
                and not u.password
                and not any(c.isspace() or ord(c) < 32 for c in link)
            )
            _ = u.port
        except ValueError:
            valid = False
        if not valid:
            raise AppError(422, "INVALID_EVIDENCE_LINK")


async def bindable(
    db: AsyncSession,
    a: RitualAssignment,
    o: RitualOccurrence,
    uid: UUID,
    body: ReportCommand,
    now: datetime,
) -> list[RitualEvidence]:
    validate_links(body.links)
    if (
        len(body.evidence_ids) != len(set(body.evidence_ids))
        or len(body.evidence_ids) + len(body.links) > 3
    ):
        raise AppError(422, "INVALID_EVIDENCE")
    policy = EvidencePolicy.model_validate(a.evidence_policy)
    if policy.required and not (body.links or body.evidence_ids):
        raise AppError(422, "EVIDENCE_REQUIRED")
    if body.links and "link" not in policy.allowed_types:
        raise AppError(422, "EVIDENCE_TYPE_DENIED")
    rows = list(
        (
            await db.scalars(
                select(RitualEvidence)
                .where(RitualEvidence.id.in_(body.evidence_ids))
                .order_by(RitualEvidence.id)
                .with_for_update()
            )
        ).all()
    )
    if len(rows) != len(body.evidence_ids) or any(
        e.occurrence_id != o.id
        or e.owner_id != uid
        or e.report_id is not None
        or e.expires_at is None
        or e.expires_at <= now
        or e.kind not in policy.allowed_types
        for e in rows
    ):
        raise AppError(422, "INVALID_EVIDENCE")
    return rows


def view(e: RitualEvidence) -> EvidenceView:
    return EvidenceView(id=e.id, kind=e.kind, media_type=e.media_type, size=e.size)


def decode(body: EvidenceUpload) -> bytes:
    try:
        data = base64.b64decode(body.data_base64, validate=True)
    except (ValueError, binascii.Error):
        raise AppError(422, "INVALID_MEDIA") from None
    if not 0 < len(data) <= 8 * 1024 * 1024:
        raise AppError(413, "MEDIA_TOO_LARGE")
    valid = {
        "image/png": data.startswith(b"\x89PNG\r\n\x1a\n") and data.endswith(b"IEND\xaeB`\x82"),
        "image/jpeg": data.startswith(b"\xff\xd8\xff") and data.endswith(b"\xff\xd9"),
        "video/mp4": len(data) >= 16
        and data[4:8] == b"ftyp"
        and 16 <= int.from_bytes(data[:4], "big") <= len(data),
        "video/webm": data.startswith(b"\x1a\x45\xdf\xa3") and b"webm" in data[:4096],
    }[body.media_type]
    if not valid or (body.kind == "photo") != body.media_type.startswith("image/"):
        raise AppError(422, "INVALID_MEDIA")
    return data


@router.post("/ritual-occurrences/{oid}/evidence", response_model=EvidenceView)
async def upload(
    oid: UUID, body: EvidenceUpload, principal: Member, db: DB, request: Request
) -> EvidenceView:
    # Serializes the member quota across different occurrences; same order as account disable.
    await db.get(User, principal.user_id, with_for_update=True)
    a, o = await service.locked(db, oid)
    now = request.app.state.clock.now()
    if a.recipient_id != principal.user_id or not await service.effective(db, a):
        raise AppError(403, "ACCESS_DENIED")
    if o.status not in ("scheduled", "needs_changes") or not o.due_at <= now < o.expires_at:
        raise AppError(409, "OCCURRENCE_CLOSED")
    if body.kind not in EvidencePolicy.model_validate(a.evidence_policy).allowed_types:
        raise AppError(422, "EVIDENCE_TYPE_DENIED")
    data = decode(body)
    digest = hashlib.sha256(data).digest()
    previous = await db.scalar(
        select(RitualEvidence).where(
            RitualEvidence.occurrence_id == oid,
            RitualEvidence.idempotency_key == body.idempotency_key,
        )
    )
    if previous:
        if (
            previous.digest != digest
            or previous.kind != body.kind
            or previous.media_type != body.media_type
        ):
            raise AppError(409, "IDEMPOTENCY_CONFLICT")
        return view(previous)
    owner_size = (
        await db.scalar(
            select(func.coalesce(func.sum(RitualEvidence.size), 0)).where(
                RitualEvidence.owner_id == principal.user_id
            )
        )
    ) or 0
    occurrence_size = (
        await db.scalar(
            select(func.coalesce(func.sum(RitualEvidence.size), 0)).where(
                RitualEvidence.occurrence_id == oid
            )
        )
    ) or 0
    staged = (
        await db.scalar(
            select(func.count())
            .select_from(RitualEvidence)
            .where(RitualEvidence.occurrence_id == oid, RitualEvidence.report_id.is_(None))
        )
    ) or 0
    if (
        staged >= 3
        or owner_size + len(data) > 128 * 1024 * 1024
        or occurrence_size + len(data) > 32 * 1024 * 1024
    ):
        raise AppError(413, "EVIDENCE_QUOTA")
    eid = uuid4()
    stored = cipher_for(request).seal_payload("ritual_evidence", eid, 1, data)
    e = RitualEvidence(
        id=eid,
        occurrence_id=oid,
        owner_id=principal.user_id,
        idempotency_key=body.idempotency_key,
        digest=digest,
        kind=body.kind,
        media_type=body.media_type,
        size=len(data),
        created_at=now,
        expires_at=now + timedelta(hours=24),
        key_id=stored.key_id,
        nonce=stored.nonce,
        ciphertext=stored.ciphertext,
    )
    db.add(e)
    return view(e)


@router.get("/ritual-evidence/{eid}", response_model=EvidenceDownload)
async def download(eid: UUID, principal: Member, db: DB, request: Request) -> EvidenceDownload:
    e = await db.get(RitualEvidence, eid)
    if e is None:
        raise AppError(404, "NOT_FOUND")
    o = await db.get(RitualOccurrence, e.occurrence_id)
    assert o is not None
    a = await db.get(RitualAssignment, o.assignment_id)
    assert a is not None
    if e.report_id is None:
        permitted = (
            e.owner_id == principal.user_id
            and e.expires_at is not None
            and e.expires_at > request.app.state.clock.now()
        )
    else:
        permitted = await service.visible(db, a, principal.user_id)
    if not permitted:
        raise AppError(404, "NOT_FOUND")
    data = cipher_for(request).open_payload(
        "ritual_evidence", e.id, 1, EncryptedEnvelope(e.key_id, e.nonce, e.ciphertext)
    )
    return EvidenceDownload(**view(e).model_dump(), data_base64=base64.b64encode(data).decode())


@router.delete("/ritual-evidence/{eid}", status_code=204)
async def discard(eid: UUID, principal: Member, db: DB) -> None:
    e = await db.get(RitualEvidence, eid, with_for_update=True)
    if e is None or e.owner_id != principal.user_id or e.report_id is not None:
        raise AppError(404, "NOT_FOUND")
    await db.delete(e)


@router.get("/ritual-occurrences/{oid}/evidence", response_model=list[EvidenceView])
async def staged(oid: UUID, principal: Member, db: DB, request: Request) -> list[EvidenceView]:
    o = await db.get(RitualOccurrence, oid)
    a = await db.get(RitualAssignment, o.assignment_id) if o else None
    if a is None or a.recipient_id != principal.user_id:
        raise AppError(404, "NOT_FOUND")
    rows = (
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
            .where(
                RitualEvidence.occurrence_id == oid,
                RitualEvidence.owner_id == principal.user_id,
                RitualEvidence.report_id.is_(None),
                RitualEvidence.expires_at > request.app.state.clock.now(),
            )
            .order_by(RitualEvidence.created_at, RitualEvidence.id)
        )
    ).all()
    return [view(e) for e in rows]
