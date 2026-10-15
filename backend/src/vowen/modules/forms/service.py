import hashlib
import json
import secrets
from datetime import datetime, timedelta
from uuid import UUID, uuid4

from pydantic import JsonValue
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from vowen.core.crypto import EncryptedEnvelope, PayloadCipher
from vowen.core.errors import AppError
from vowen.modules.forms.models import (
    BotContact,
    Delivery,
    Form,
    FormVersion,
    GuestSession,
    Invitation,
    InvitationReader,
    Receipt,
    Submission,
)
from vowen.modules.forms.schemas import (
    FormAccess,
    FormEdit,
    FormSchema,
    FormView,
    InvitationCreate,
    InvitationView,
    ReaderView,
    SubmissionView,
    Submit,
    validate_answers,
)
from vowen.modules.identity.models import User


def digest(value: str) -> bytes:
    return hashlib.sha256(value.encode()).digest()


def seal(row: Submission | Delivery, cipher: PayloadCipher, payload: dict[str, JsonValue]) -> None:
    kind = "form_submission" if isinstance(row, Submission) else "delivery"
    e = cipher.seal_payload(kind, row.id, 1, json.dumps(payload, allow_nan=False).encode())
    row.key_id, row.nonce, row.ciphertext = e.key_id, e.nonce, e.ciphertext


def clear(row: Submission | Delivery) -> None:
    row.key_id = row.nonce = row.ciphertext = None


def opened(row: Submission | Delivery, cipher: PayloadCipher) -> dict[str, JsonValue]:
    if row.ciphertext is None:
        return {}
    assert row.key_id is not None and row.nonce is not None
    kind = "form_submission" if isinstance(row, Submission) else "delivery"
    result: dict[str, JsonValue] = json.loads(
        cipher.open_payload(
            kind, row.id, 1, EncryptedEnvelope(row.key_id, row.nonce, row.ciphertext)
        )
    )
    return result


async def active(db: AsyncSession, user_id: UUID) -> None:
    u = await db.get(User, user_id)
    if u is None or not u.is_active or u.paused:
        raise AppError(403, "ACCESS_DENIED")


async def form_owned(db: AsyncSession, fid: UUID, uid: UUID) -> Form:
    f = await db.get(Form, fid, with_for_update=True)
    if f is None or f.author_id != uid:
        raise AppError(404, "NOT_FOUND")
    return f


async def form_view(db: AsyncSession, f: Form) -> FormView:
    v = await db.get(FormVersion, f.current_version_id)
    assert v is not None
    return FormView(
        id=f.id,
        version_id=v.id,
        revision=f.revision,
        status=v.status,
        schema_body=FormSchema.model_validate(v.schema_body),
    )


async def create_form(db: AsyncSession, uid: UUID, body: FormSchema) -> FormView:
    await active(db, uid)
    fid, vid = uuid4(), uuid4()
    f = Form(id=fid, author_id=uid, current_version_id=vid)
    db.add(f)
    await db.flush()
    db.add(FormVersion(id=vid, form_id=fid, schema_body=body.model_dump(mode="json")))
    await db.flush()
    return await form_view(db, f)


async def edit_form(
    db: AsyncSession, uid: UUID, fid: UUID, body: FormEdit | None, expected: int, action: str
) -> FormView:
    await active(db, uid)
    f = await form_owned(db, fid, uid)
    v = await db.get(FormVersion, f.current_version_id)
    assert v is not None
    if f.revision != expected:
        raise AppError(409, "VERSION_CONFLICT")
    if action == "versions":
        assert body is not None
        nv = FormVersion(
            id=uuid4(), form_id=f.id, schema_body=body.schema_body.model_dump(mode="json")
        )
        db.add(nv)
        f.current_version_id = nv.id
    elif action == "edit":
        if v.status != "draft":
            raise AppError(409, "IMMUTABLE_VERSION")
        assert body is not None
        v.schema_body = body.schema_body.model_dump(mode="json")
    elif action == "publish":
        if v.status != "draft":
            raise AppError(409, "IMMUTABLE_VERSION")
        v.status = "published"
    else:
        v.status = "archived"
    f.revision += 1
    await db.flush()
    return await form_view(db, f)


async def readers(db: AsyncSession, i: Invitation) -> list[ReaderView]:
    rows = (
        await db.execute(
            select(User.id, User.display_name)
            .join(InvitationReader, InvitationReader.user_id == User.id)
            .where(InvitationReader.invitation_id == i.id)
        )
    ).all()
    return [ReaderView(id=r.id, display_name=r.display_name) for r in rows]


async def invitation_view(
    db: AsyncSession, i: Invitation, link: str | None = None
) -> InvitationView:
    d = await db.scalar(
        select(Delivery).where(Delivery.invitation_id == i.id, Delivery.kind == "invitation")
    )
    return InvitationView(
        id=i.id,
        version_id=i.version_id,
        recipient_user_id=i.recipient_user_id,
        expires_at=i.expires_at.isoformat(),
        retention_until=i.retention_until.isoformat(),
        revoked=i.revoked_at is not None,
        delivery_status=d.status if d else "manual_delivery_required",
        link=link,
    )


async def invite(
    db: AsyncSession,
    uid: UUID,
    fid: UUID,
    body: InvitationCreate,
    now: datetime,
    base: str,
    cipher: PayloadCipher,
) -> InvitationView:
    await active(db, uid)
    f = await form_owned(db, fid, uid)
    v = await db.get(FormVersion, f.current_version_id)
    if v is None or v.status != "published":
        raise AppError(409, "PUBLISH_REQUIRED")
    selected = set(body.reader_ids) | (
        {body.recipient_user_id} if body.recipient_user_id else set()
    )
    count = (await db.scalars(select(User.id).where(User.id.in_(selected), User.is_active))).all()
    if set(count) != selected:
        raise AppError(422, "INVALID_AUDIENCE")
    secret = secrets.token_urlsafe(32) if body.recipient_user_id is None else None
    i = Invitation(
        id=uuid4(),
        version_id=v.id,
        creator_id=uid,
        recipient_user_id=body.recipient_user_id,
        token_hash=digest(secret) if secret else None,
        expires_at=now + timedelta(days=body.ttl_days),
        retention_until=now + timedelta(days=body.retention_days),
    )
    db.add(i)
    await db.flush()
    db.add_all([InvitationReader(invitation_id=i.id, user_id=r) for r in body.reader_ids])
    db.add(Submission(id=uuid4(), invitation_id=i.id))
    link = base.rstrip("/") + (f"/f/{i.id}#token={secret}" if secret else f"/?invitation={i.id}")
    telegram_id = body.contact_telegram_id
    if body.recipient_user_id:
        u = await db.get(User, body.recipient_user_id)
        assert u is not None
        telegram_id = u.telegram_id
    if body.deliver and telegram_id:
        contact = await db.get(BotContact, telegram_id)
        if contact and contact.allowed:
            d = Delivery(id=uuid4(), invitation_id=i.id, telegram_id=telegram_id)
            seal(d, cipher, {"link": link})
            db.add(d)
    await db.flush()
    return await invitation_view(db, i, link)


async def locked_invitation(db: AsyncSession, iid: UUID) -> Invitation:
    i = await db.get(Invitation, iid, with_for_update=True)
    if i is None:
        raise AppError(404, "NOT_FOUND")
    return i


def live(i: Invitation, now: datetime) -> None:
    if i.revoked_at is not None or i.expires_at <= now or i.retention_until <= now:
        raise AppError(410, "INVITATION_CLOSED")


async def submission(db: AsyncSession, i: Invitation) -> Submission:
    s = await db.scalar(select(Submission).where(Submission.invitation_id == i.id))
    assert s is not None
    return s


async def access(
    db: AsyncSession, i: Invitation, cipher: PayloadCipher, csrf: str | None = None
) -> FormAccess:
    v = await db.get(FormVersion, i.version_id)
    assert v is not None
    s = await submission(db, i)
    return FormAccess(
        id=i.id,
        schema_body=FormSchema.model_validate(v.schema_body),
        readers=await readers(db, i),
        retention_until=i.retention_until.isoformat(),
        status=s.status,
        answers=opened(s, cipher),
        csrf_token=csrf,
    )


async def write_answers(
    db: AsyncSession,
    i: Invitation,
    answers: dict[str, JsonValue],
    cipher: PayloadCipher,
    now: datetime,
    command: Submit | None = None,
    base: str = "",
) -> Submission:
    live(i, now)
    s = await submission(db, i)
    if s.status == "submitted" and command and s.idempotency_key == command.idempotency_key:
        return s
    if s.status != "draft":
        raise AppError(409, "ALREADY_FINALIZED")
    v = await db.get(FormVersion, i.version_id)
    assert v is not None
    try:
        clean = validate_answers(
            FormSchema.model_validate(v.schema_body), answers, final=command is not None
        )
    except ValueError:
        raise AppError(422, "INVALID_ANSWERS") from None
    seal(s, cipher, clean)
    if command:
        s.status, s.idempotency_key = "submitted", command.idempotency_key
        audience = (
            await db.scalars(
                select(User)
                .join(InvitationReader, InvitationReader.user_id == User.id)
                .where(InvitationReader.invitation_id == i.id, User.is_active, ~User.paused)
            )
        ).all()
        for reader in audience:
            contact = await db.get(BotContact, reader.telegram_id)
            if contact and contact.allowed:
                notification = Delivery(
                    id=uuid4(), invitation_id=i.id, telegram_id=reader.telegram_id, kind="response"
                )
                seal(notification, cipher, {"link": base.rstrip("/") + "/?submission=" + str(s.id)})
                db.add(notification)
    await db.flush()
    return s


async def result_view(
    db: AsyncSession, i: Invitation, s: Submission, cipher: PayloadCipher, own: bool = False
) -> SubmissionView:
    a = await access(db, i, cipher)
    return SubmissionView(
        can_delete=own,
        id=s.id,
        invitation_id=i.id,
        schema_body=a.schema_body,
        readers=a.readers,
        status=s.status,
        answers=a.answers,
    )


async def withdraw(db: AsyncSession, s: Submission, now: datetime) -> None:
    s.status = "withdrawn"
    clear(s)
    notifications = (
        await db.scalars(
            select(Delivery).where(
                Delivery.invitation_id == s.invitation_id, Delivery.kind == "response"
            )
        )
    ).all()
    for notification in notifications:
        clear(notification)
        notification.status = "cancelled"
    await db.execute(
        delete(InvitationReader).where(InvitationReader.invitation_id == s.invitation_id)
    )
    receipts = (await db.scalars(select(Receipt).where(Receipt.submission_id == s.id))).all()
    for r in receipts:
        r.revoked_at = now


async def new_guest(
    db: AsyncSession, i: Invitation, now: datetime, receipt: Receipt | None = None
) -> tuple[str, str]:
    token, csrf = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
    expiry = receipt.expires_at if receipt else i.expires_at
    db.add(
        GuestSession(
            invitation_id=i.id,
            receipt_id=receipt.id if receipt else None,
            token_hash=digest(token),
            csrf_hash=digest(csrf),
            expires_at=min(now + timedelta(hours=24), expiry),
        )
    )
    await db.flush()
    return token, csrf
