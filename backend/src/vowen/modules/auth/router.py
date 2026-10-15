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
from vowen.modules.auth.models import Session
from vowen.modules.auth.schemas import (
    InstanceView,
    MemberView,
    MiniAppLogin,
    RefreshRequest,
    SessionTokens,
    SessionView,
)
from vowen.modules.auth.service import (
    MemberPrincipal,
    authenticate_miniapp,
    resolve_member,
    rotate_refresh,
)
from vowen.modules.identity.models import User

router = APIRouter(prefix="/api/v1")


async def transaction(request: Request) -> AsyncIterator[AsyncSession]:
    if not await check_schema(request.app.state.engine):
        raise AppError(503, "UNAVAILABLE")
    async with request.app.state.sessions() as db:
        async with db.begin():
            yield db


DB = Annotated[AsyncSession, Depends(transaction)]
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
    return MemberView(id=user.id, display_name=user.display_name, paused=user.paused)


@router.get("/participants", response_model=list[MemberView])
async def participants(principal: Member, db: DB) -> list[MemberView]:
    users = (await db.scalars(select(User).where(User.is_active))).all()
    return [MemberView(id=u.id, display_name=u.display_name, paused=u.paused) for u in users]


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
    return InstanceView(display_name=request.app.state.settings.app_display_name)
