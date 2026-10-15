from collections.abc import AsyncIterator
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Request, Response
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from vowen.core.database import check_schema
from vowen.core.errors import AppError
from vowen.modules.auth.android_challenge import (
    ChallengeCreated,
    ChallengeProof,
    ChallengeRequest,
    ChallengeStatus,
    check_proof,
    consume_challenge,
    create_challenge,
)
from vowen.modules.auth.debug import debug_available, debug_transaction
from vowen.modules.auth.models import Session
from vowen.modules.auth.schemas import (
    DebugLogin,
    DebugUserView,
    InstanceView,
    MemberView,
    MiniAppLogin,
    ParticipantView,
    RefreshRequest,
    SessionTokens,
    SessionView,
)
from vowen.modules.auth.service import (
    MemberPrincipal,
    authenticate_miniapp,
    create_session,
    resolve_member,
    rotate_refresh,
)
from vowen.modules.identity.models import User, UserPreferences
from vowen.modules.identity.profile import profile_view, update_profile
from vowen.modules.identity.schemas import ProfilePatch

router = APIRouter(prefix="/api/v1")


async def transaction(request: Request) -> AsyncIterator[AsyncSession]:
    if not await check_schema(request.app.state.engine):
        raise AppError(503, "UNAVAILABLE")
    async with request.app.state.sessions() as db:
        async with db.begin():
            yield db


# Commit/rollback must finish before any success body or Set-Cookie leaves the server.
DB = Annotated[AsyncSession, Depends(transaction, scope="function")]
bearer = HTTPBearer(auto_error=False)


async def member(
    request: Request,
    db: DB,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
) -> MemberPrincipal:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise AppError(401, "INVALID_AUTH")
    return await resolve_member(db, credentials.credentials, request.app.state.clock.now())


Member = Annotated[MemberPrincipal, Depends(member)]
DebugDB = Annotated[AsyncSession, Depends(debug_transaction, scope="function")]


@router.get("/auth/debug/users", response_model=list[DebugUserView])
async def debug_users(db: DebugDB) -> list[DebugUserView]:
    users = await db.scalars(
        select(User).where(User.is_active).order_by(User.display_name, User.id)
    )
    return [DebugUserView(id=user.id, display_name=user.display_name) for user in users]


@router.post("/auth/debug", response_model=SessionTokens)
async def debug_login(body: DebugLogin, request: Request, db: DebugDB) -> SessionTokens:
    user = await db.scalar(select(User).where(User.id == body.user_id).with_for_update())
    if user is None or not user.is_active:
        raise AppError(403, "ACCESS_DENIED")
    return await create_session(
        db, user, "debug", "Local development", request.app.state.clock.now()
    )


@router.post("/auth/telegram/miniapp", response_model=SessionTokens)
async def miniapp(body: MiniAppLogin, request: Request, db: DB) -> SessionTokens:
    try:
        token = request.app.state.settings.bot_token()
    except (OSError, RuntimeError):
        raise AppError(503, "UNAVAILABLE") from None
    return await authenticate_miniapp(db, body.init_data, token, request.app.state.clock.now())


@router.post("/auth/refresh", response_model=SessionTokens)
async def refresh(body: RefreshRequest, request: Request, db: DB) -> SessionTokens:
    return await rotate_refresh(db, body.refresh_token, request.app.state.clock.now())


@router.get("/me", response_model=MemberView)
async def me(principal: Member, db: DB) -> MemberView:
    user = await db.get(User, principal.user_id)
    assert user is not None
    return await profile_view(db, user)


@router.patch("/me/preferences", response_model=MemberView)
async def preferences(body: ProfilePatch, principal: Member, db: DB) -> MemberView:
    return await update_profile(db, principal.user_id, body)


@router.get("/participants", response_model=list[ParticipantView])
async def participants(principal: Member, db: DB) -> list[ParticipantView]:
    rows = (
        await db.execute(select(User, UserPreferences).join(UserPreferences).where(User.is_active))
    ).all()
    return [
        ParticipantView(id=u.id, display_name=u.display_name, profile_labels=p.profile_labels)
        for u, p in rows
    ]


@router.get("/sessions", response_model=list[SessionView])
async def sessions(principal: Member, db: DB) -> list[Session]:
    return list(
        (await db.scalars(select(Session).where(Session.user_id == principal.user_id))).all()
    )


async def revoke_owned(db: AsyncSession, principal: MemberPrincipal, session_id: UUID) -> None:
    family = await db.scalar(
        select(Session)
        .where(Session.id == session_id, Session.user_id == principal.user_id)
        .with_for_update()
    )
    if family is None:
        raise AppError(404, "NOT_FOUND")
    family.revoked = True


@router.delete("/sessions/{session_id}", status_code=204)
async def revoke(session_id: UUID, principal: Member, db: DB) -> Response:
    await revoke_owned(db, principal, session_id)
    return Response(status_code=204)


@router.post("/auth/logout", status_code=204)
async def logout(principal: Member, db: DB) -> Response:
    await revoke_owned(db, principal, principal.session_id)
    return Response(status_code=204)


@router.post("/auth/android/challenges", response_model=ChallengeCreated)
async def android_create(body: ChallengeRequest, request: Request, db: DB) -> ChallengeCreated:
    return await create_challenge(
        db,
        body.client_nonce,
        body.device_label,
        request.app.state.settings.telegram_bot_username,
        request.app.state.clock.now(),
    )


@router.post("/auth/android/challenges/{challenge_id}/status", response_model=ChallengeStatus)
async def android_status(
    challenge_id: UUID, body: ChallengeProof, request: Request, db: DB
) -> ChallengeStatus:
    challenge = await check_proof(
        db, challenge_id, body.poll_secret, body.client_nonce, request.app.state.clock.now()
    )
    return ChallengeStatus(status=challenge.status)


@router.post("/auth/android/challenges/{challenge_id}/consume", response_model=SessionTokens)
async def android_consume(
    challenge_id: UUID, body: ChallengeProof, request: Request, db: DB
) -> SessionTokens:
    return await consume_challenge(
        db, challenge_id, body.poll_secret, body.client_nonce, request.app.state.clock.now()
    )


@router.get("/instance", response_model=InstanceView)
async def instance(request: Request) -> InstanceView:
    return InstanceView(
        display_name=request.app.state.settings.app_display_name,
        debug_auth_enabled=debug_available(request),
    )
