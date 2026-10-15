import hmac
import secrets
from datetime import datetime
from typing import Annotated
from urllib.parse import urlsplit
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy import or_, select, update

from vowen.core.crypto import PayloadCipher
from vowen.core.errors import AppError
from vowen.modules.auth.router import DB, Member
from vowen.modules.forms import service as svc
from vowen.modules.forms.models import (
    Form,
    FormVersion,
    GuestSession,
    Invitation,
    InvitationReader,
    Receipt,
    Submission,
)
from vowen.modules.forms.schemas import (
    Answers,
    Exchange,
    FormAccess,
    FormEdit,
    FormSchema,
    FormView,
    GuestSessionView,
    InvitationCreate,
    InvitationView,
    SubmissionView,
    Submit,
)
from vowen.modules.relations.schemas import ExpectedVersion

router = APIRouter(prefix="/api/v1")
COOKIE = "__Host-vowen_guest"


def cipher(request: Request) -> PayloadCipher:
    try:
        return PayloadCipher(request.app.state.settings.data_keyring_file)
    except (OSError, ValueError):
        raise AppError(503, "UNAVAILABLE") from None


Cipher = Annotated[PayloadCipher, Depends(cipher)]


def now(request: Request) -> datetime:
    value: datetime = request.app.state.clock.now()
    return value


def origin(request: Request) -> None:
    base = urlsplit(request.app.state.settings.public_base_url)
    if request.headers.get("origin") != f"{base.scheme}://{base.netloc}":
        raise AppError(403, "INVALID_ORIGIN")


def set_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        COOKIE, token, max_age=86400, secure=True, httponly=True, samesite="lax", path="/"
    )


@router.post("/forms", response_model=FormView)
async def create(body: FormSchema, principal: Member, db: DB) -> FormView:
    return await svc.create_form(db, principal.user_id, body)


@router.get("/forms", response_model=list[FormView])
async def forms(principal: Member, db: DB) -> list[FormView]:
    rows = (await db.scalars(select(Form).where(Form.author_id == principal.user_id))).all()
    return [await svc.form_view(db, f) for f in rows]


@router.get("/forms/{fid}", response_model=FormView)
async def form(fid: UUID, principal: Member, db: DB) -> FormView:
    return await svc.form_view(db, await svc.form_owned(db, fid, principal.user_id))


@router.patch("/forms/{fid}", response_model=FormView)
async def edit(fid: UUID, body: FormEdit, principal: Member, db: DB) -> FormView:
    return await svc.edit_form(db, principal.user_id, fid, body, body.expected_version, "edit")


@router.post("/forms/{fid}/versions", response_model=FormView)
async def version(fid: UUID, body: FormEdit, principal: Member, db: DB) -> FormView:
    return await svc.edit_form(db, principal.user_id, fid, body, body.expected_version, "versions")


@router.post("/forms/{fid}/publish", response_model=FormView)
async def publish(fid: UUID, body: ExpectedVersion, principal: Member, db: DB) -> FormView:
    return await svc.edit_form(db, principal.user_id, fid, None, body.expected_version, "publish")


@router.post("/forms/{fid}/archive", response_model=FormView)
async def archive(fid: UUID, body: ExpectedVersion, principal: Member, db: DB) -> FormView:
    return await svc.edit_form(db, principal.user_id, fid, None, body.expected_version, "archive")


@router.post("/forms/{fid}/invitations", response_model=InvitationView)
async def invite(
    fid: UUID, body: InvitationCreate, request: Request, principal: Member, db: DB, crypto: Cipher
) -> InvitationView:
    return await svc.invite(
        db,
        principal.user_id,
        fid,
        body,
        now(request),
        request.app.state.settings.public_base_url,
        crypto,
    )


@router.get("/forms/{fid}/invitations", response_model=list[InvitationView])
async def invitations(fid: UUID, principal: Member, db: DB) -> list[InvitationView]:
    await svc.form_owned(db, fid, principal.user_id)
    rows = (
        await db.scalars(
            select(Invitation)
            .join(FormVersion)
            .where(Invitation.creator_id == principal.user_id, FormVersion.form_id == fid)
        )
    ).all()
    return [await svc.invitation_view(db, i) for i in rows]


@router.delete("/forms/invitations/{iid}", status_code=204)
async def revoke(iid: UUID, request: Request, principal: Member, db: DB) -> Response:
    i = await svc.locked_invitation(db, iid)
    if i.creator_id != principal.user_id:
        raise AppError(404, "NOT_FOUND")
    i.revoked_at = now(request)
    s = await svc.submission(db, i)
    if s.status == "draft":
        svc.clear(s)
    return Response(status_code=204)


@router.delete("/forms/invitations/{iid}/readers/{uid}", status_code=204)
async def remove_reader(iid: UUID, uid: UUID, principal: Member, db: DB) -> Response:
    i = await svc.locked_invitation(db, iid)
    if principal.user_id not in (i.creator_id, uid):
        raise AppError(404, "NOT_FOUND")
    row = await db.get(InvitationReader, (iid, uid))
    if row:
        await db.delete(row)
    return Response(status_code=204)


async def member_invitation(db: DB, iid: UUID, uid: UUID, request: Request) -> Invitation:
    i = await svc.locked_invitation(db, iid)
    if i.recipient_user_id != uid:
        raise AppError(404, "NOT_FOUND")
    svc.live(i, now(request))
    return i


@router.get("/form-invitations", response_model=list[FormAccess])
async def assigned(request: Request, principal: Member, db: DB, crypto: Cipher) -> list[FormAccess]:
    ids = (
        await db.scalars(
            select(Invitation.id).where(
                Invitation.recipient_user_id == principal.user_id,
                Invitation.revoked_at.is_(None),
                Invitation.expires_at > now(request),
                or_(
                    Invitation.retention_until.is_(None), Invitation.retention_until > now(request)
                ),
            )
        )
    ).all()
    return [
        await svc.access(db, await member_invitation(db, i, principal.user_id, request), crypto)
        for i in ids
    ]


@router.get("/form-invitations/{iid}", response_model=FormAccess)
async def assigned_form(
    iid: UUID, request: Request, principal: Member, db: DB, crypto: Cipher
) -> FormAccess:
    return await svc.access(
        db, await member_invitation(db, iid, principal.user_id, request), crypto
    )


@router.put("/form-invitations/{iid}/draft", response_model=FormAccess)
async def draft(
    iid: UUID, body: Answers, request: Request, principal: Member, db: DB, crypto: Cipher
) -> FormAccess:
    await svc.active(db, principal.user_id)
    i = await member_invitation(db, iid, principal.user_id, request)
    await svc.write_answers(db, i, body.answers, crypto, now(request))
    return await svc.access(db, i, crypto)


@router.post("/form-invitations/{iid}/submit", response_model=SubmissionView)
async def submit(
    iid: UUID, body: Submit, request: Request, principal: Member, db: DB, crypto: Cipher
) -> SubmissionView:
    await svc.active(db, principal.user_id)
    i = await member_invitation(db, iid, principal.user_id, request)
    s = await svc.write_answers(
        db,
        i,
        body.answers,
        crypto,
        now(request),
        body,
        base=request.app.state.settings.public_base_url,
    )
    return await svc.result_view(db, i, s, crypto, own=True)


async def readable(db: DB, sid: UUID, uid: UUID, request: Request) -> tuple[Invitation, Submission]:
    s = await db.get(Submission, sid)
    if s is None:
        raise AppError(404, "NOT_FOUND")
    i = await svc.locked_invitation(db, s.invitation_id)
    await db.refresh(s)
    reader = await db.get(InvitationReader, (i.id, uid))
    if (
        s.status != "submitted"
        or i.retention_until is None
        or i.retention_until <= now(request)
        or (i.recipient_user_id != uid and reader is None)
    ):
        raise AppError(404, "NOT_FOUND")
    return i, s


@router.get("/form-submissions", response_model=list[SubmissionView])
async def results(
    request: Request, principal: Member, db: DB, crypto: Cipher
) -> list[SubmissionView]:
    ids = (
        await db.scalars(
            select(Submission.id)
            .join(Invitation)
            .where(
                Submission.status == "submitted",
                Invitation.retention_until > now(request),
                (Invitation.recipient_user_id == principal.user_id)
                | Invitation.id.in_(
                    select(InvitationReader.invitation_id).where(
                        InvitationReader.user_id == principal.user_id
                    )
                ),
            )
        )
    ).all()
    result = []
    for sid in ids:
        try:
            i, s = await readable(db, sid, principal.user_id, request)
        except AppError as error:
            if error.status != 404:
                raise
            continue
        result.append(
            await svc.result_view(db, i, s, crypto, own=i.recipient_user_id == principal.user_id)
        )
    return result


@router.get("/form-submissions/{sid}", response_model=SubmissionView)
async def result(
    sid: UUID, request: Request, principal: Member, db: DB, crypto: Cipher
) -> SubmissionView:
    i, s = await readable(db, sid, principal.user_id, request)
    return await svc.result_view(db, i, s, crypto, own=i.recipient_user_id == principal.user_id)


@router.delete("/form-submissions/{sid}", status_code=204)
async def remove(sid: UUID, request: Request, principal: Member, db: DB) -> Response:
    i, s = await readable(db, sid, principal.user_id, request)
    if i.recipient_user_id != principal.user_id:
        raise AppError(404, "NOT_FOUND")
    await svc.withdraw(db, s, now(request))
    return Response(status_code=204)


async def guest(
    request: Request,
    db: DB,
    *,
    writing: bool = False,
    filling: bool = False,
    check_context: bool = True,
) -> tuple[GuestSession, Invitation]:
    if writing:
        origin(request)
    token = request.cookies.get(COOKIE, "")
    gs = await db.scalar(select(GuestSession).where(GuestSession.token_hash == svc.digest(token)))
    if gs is None or gs.expires_at <= now(request):
        raise AppError(401, "INVALID_GUEST_SESSION")
    i = await svc.locked_invitation(db, gs.invitation_id)
    expected = request.headers.get("x-guest-context")
    if check_context and expected and expected != str(gs.receipt_id or i.id):
        raise AppError(409, "GUEST_CONTEXT_CHANGED")
    if writing and not hmac.compare_digest(
        gs.csrf_hash, svc.digest(request.headers.get("x-csrf-token", ""))
    ):
        raise AppError(403, "INVALID_CSRF")
    if gs.receipt_id:
        receipt = await db.get(Receipt, gs.receipt_id)
        if receipt is None or receipt.revoked_at or receipt.expires_at <= now(request):
            raise AppError(401, "INVALID_RECEIPT")
        if filling:
            raise AppError(403, "SCOPE_DENIED")
    else:
        svc.live(i, now(request))
    if i.retention_until is not None and i.retention_until <= now(request):
        raise AppError(410, "RESPONSE_EXPIRED")
    return gs, i


async def replacement(
    request: Request, db: DB, proof: Exchange, iid: UUID, receipt_id: UUID | None
) -> GuestSession | None:
    token = request.cookies.get(COOKIE)
    if not token:
        return None
    old = await db.scalar(select(GuestSession).where(GuestSession.token_hash == svc.digest(token)))
    if old is None or old.expires_at <= now(request):
        return None
    prior = await db.get(Invitation, old.invitation_id)
    if prior is None:
        return None
    if old.receipt_id:
        prior_receipt = await db.get(Receipt, old.receipt_id)
        if (
            prior_receipt is None
            or prior_receipt.revoked_at
            or prior_receipt.expires_at <= now(request)
        ):
            return None
    elif prior.revoked_at or prior.expires_at <= now(request):
        return None
    if prior.retention_until is not None and prior.retention_until <= now(request):
        return None
    if old.invitation_id == iid and old.receipt_id == receipt_id:
        return None
    if old.invitation_id == iid and old.receipt_id is None and receipt_id is not None:
        return None  # A submitted response can safely become its own read/delete receipt.
    if not proof.replace_session:
        raise AppError(409, "SESSION_REPLACEMENT_REQUIRED")
    if not hmac.compare_digest(old.csrf_hash, svc.digest(request.headers.get("x-csrf-token", ""))):
        raise AppError(403, "INVALID_CSRF")
    return old


async def abandon(db: DB, old: GuestSession | None, at: datetime) -> None:
    if old is not None:
        changed = await db.scalar(
            update(GuestSession)
            .where(GuestSession.id == old.id, GuestSession.expires_at > at)
            .values(expires_at=at)
            .returning(GuestSession.id)
        )
        if changed is None:
            raise AppError(409, "GUEST_CONTEXT_CHANGED")


@router.get("/guest/session", response_model=GuestSessionView)
async def guest_context(request: Request, db: DB) -> GuestSessionView:
    gs, i = await guest(request, db, check_context=False)
    csrf = secrets.token_urlsafe(32)
    gs.csrf_hash = svc.digest(csrf)
    return GuestSessionView(
        public_id=gs.receipt_id or i.id,
        kind="receipt" if gs.receipt_id else "invitation",
        csrf_token=csrf,
    )


@router.post("/guest/invitations/exchange", response_model=FormAccess)
async def exchange(
    body: Exchange, request: Request, response: Response, db: DB, crypto: Cipher
) -> FormAccess:
    origin(request)
    i = await svc.locked_invitation(db, body.public_id)
    svc.live(i, now(request))
    if i.token_hash is None or not hmac.compare_digest(i.token_hash, svc.digest(body.token)):
        raise AppError(401, "INVALID_INVITATION")
    old = await replacement(request, db, body, i.id, None)
    if i.activated_at:
        gs, owned = (
            await guest(request, db, filling=True) if request.cookies.get(COOKIE) else (None, None)
        )
        if gs is None or owned is None or owned.id != i.id:
            raise AppError(409, "ALREADY_ACTIVATED")
        csrf = secrets.token_urlsafe(32)
        gs.csrf_hash = svc.digest(csrf)
    else:
        await abandon(db, old, now(request))
        i.activated_at = now(request)
        token, csrf = await svc.new_guest(db, i, now(request))
        set_cookie(response, token)
    return await svc.access(db, i, crypto, csrf, context_id=i.id, context_kind="invitation")


@router.get("/guest/form", response_model=FormAccess)
async def guest_form(request: Request, db: DB, crypto: Cipher) -> FormAccess:
    gs, i = await guest(request, db)
    csrf = secrets.token_urlsafe(32)
    gs.csrf_hash = svc.digest(csrf)
    return await svc.access(
        db,
        i,
        crypto,
        csrf,
        context_id=gs.receipt_id or i.id,
        context_kind="receipt" if gs.receipt_id else "invitation",
    )


@router.put("/guest/draft", response_model=FormAccess)
async def guest_draft(body: Answers, request: Request, db: DB, crypto: Cipher) -> FormAccess:
    _, i = await guest(request, db, writing=True, filling=True)
    await svc.write_answers(db, i, body.answers, crypto, now(request))
    return await svc.access(db, i, crypto)


@router.post("/guest/submit", response_model=SubmissionView)
async def guest_submit(body: Submit, request: Request, db: DB, crypto: Cipher) -> SubmissionView:
    _, i = await guest(request, db, writing=True, filling=True)
    s = await svc.write_answers(
        db,
        i,
        body.answers,
        crypto,
        now(request),
        body,
        base=request.app.state.settings.public_base_url,
    )
    return await svc.result_view(db, i, s, crypto, own=True)


@router.get("/guest/submission", response_model=SubmissionView)
async def guest_result(request: Request, db: DB, crypto: Cipher) -> SubmissionView:
    _, i = await guest(request, db)
    s = await svc.submission(db, i)
    if s.status != "submitted":
        raise AppError(404, "NOT_FOUND")
    return await svc.result_view(db, i, s, crypto, own=True)


@router.delete("/guest/submission", status_code=204)
async def guest_delete(request: Request, db: DB) -> Response:
    _, i = await guest(request, db, writing=True)
    s = await svc.submission(db, i)
    if s.status != "submitted":
        raise AppError(404, "NOT_FOUND")
    await svc.withdraw(db, s, now(request))
    return Response(status_code=204)


@router.post("/guest/receipt", response_model=Exchange)
async def issue_receipt(request: Request, db: DB) -> Exchange:
    _, i = await guest(request, db, writing=True, filling=True)
    s = await svc.submission(db, i)
    if s.status != "submitted":
        raise AppError(409, "SUBMIT_REQUIRED")
    old = (await db.scalars(select(Receipt).where(Receipt.submission_id == s.id))).all()
    for r in old:
        r.revoked_at = now(request)
    token = secrets.token_urlsafe(32)
    assert i.retention_until is not None
    r = Receipt(
        id=uuid4(), submission_id=s.id, token_hash=svc.digest(token), expires_at=i.retention_until
    )
    db.add(r)
    return Exchange(public_id=r.id, token=token)


@router.post("/guest/receipts/exchange", response_model=FormAccess)
async def receipt_exchange(
    body: Exchange, request: Request, response: Response, db: DB, crypto: Cipher
) -> FormAccess:
    origin(request)
    r = await db.get(Receipt, body.public_id)
    if (
        r is None
        or r.revoked_at
        or r.expires_at <= now(request)
        or not hmac.compare_digest(r.token_hash, svc.digest(body.token))
    ):
        raise AppError(401, "INVALID_RECEIPT")
    s = await db.get(Submission, r.submission_id)
    assert s is not None
    i = await svc.locked_invitation(db, s.invitation_id)
    await db.refresh(r)
    await db.refresh(s)
    if r.revoked_at or s.status != "submitted":
        raise AppError(401, "INVALID_RECEIPT")
    old = await replacement(request, db, body, i.id, r.id)
    await abandon(db, old, now(request))
    token, csrf = await svc.new_guest(db, i, now(request), r)
    set_cookie(response, token)
    return await svc.access(db, i, crypto, csrf, context_id=r.id, context_kind="receipt")
