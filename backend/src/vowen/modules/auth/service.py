import hashlib
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from vowen.core.errors import AppError
from vowen.modules.auth.models import AccessToken, RefreshToken, Session, TelegramAssertion
from vowen.modules.auth.schemas import SessionTokens
from vowen.modules.auth.telegram_validation import verify_init_data
from vowen.modules.identity.models import User


@dataclass(frozen=True)
class MemberPrincipal:
    user_id: UUID
    session_id: UUID


@dataclass(frozen=True)
class GuestPrincipal:
    invitation_id: UUID


@dataclass(frozen=True)
class OperatorContext:
    pass


def token_hash(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


async def active_user(db: AsyncSession, telegram_id: int) -> User:
    user = await db.scalar(select(User).where(User.telegram_id == telegram_id).with_for_update())
    if user is None or not user.is_active:
        raise AppError(403, "ACCESS_DENIED")
    return user


async def issue_tokens(db: AsyncSession, family: Session, now: datetime) -> SessionTokens:
    access, refresh = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
    expiry = min(now + timedelta(minutes=15), family.expires_at)
    db.add(AccessToken(token_hash=token_hash(access), session_id=family.id, expires_at=expiry))
    db.add(RefreshToken(token_hash=token_hash(refresh), session_id=family.id, spent=False))
    await db.flush()
    return SessionTokens(
        access_token=access, refresh_token=refresh, access_expires_at=expiry, session_id=family.id
    )


async def create_session(
    db: AsyncSession, user: User, client: str, label: str, now: datetime
) -> SessionTokens:
    family = Session(
        user_id=user.id,
        client=client,
        device_label=label,
        created_at=now,
        expires_at=now + (timedelta(days=30) if client == "android" else timedelta(hours=12)),
    )
    db.add(family)
    await db.flush()
    return await issue_tokens(db, family, now)


async def authenticate_miniapp(
    db: AsyncSession, raw: str, bot_token: str, now: datetime
) -> SessionTokens:
    identity = verify_init_data(raw, bot_token, now)
    user = await active_user(db, identity.telegram_id)
    try:
        async with db.begin_nested():
            db.add(
                TelegramAssertion(
                    fingerprint=identity.assertion_fingerprint,
                    expires_at=identity.auth_date + timedelta(seconds=330),
                )
            )
            await db.flush()
    except IntegrityError:
        raise AppError(401, "INVALID_AUTH") from None
    return await create_session(db, user, "miniapp", "Telegram Mini App", now)


async def resolve_member(db: AsyncSession, access_token: str, now: datetime) -> MemberPrincipal:
    row = (
        await db.execute(
            select(AccessToken, Session, User)
            .join(Session, AccessToken.session_id == Session.id)
            .join(User, Session.user_id == User.id)
            .where(AccessToken.token_hash == token_hash(access_token))
        )
    ).first()
    if row is None:
        raise AppError(401, "INVALID_AUTH")
    token, family, user = row
    if token.expires_at <= now or family.expires_at <= now or family.revoked or not user.is_active:
        raise AppError(401, "INVALID_AUTH")
    return MemberPrincipal(user.id, family.id)


async def rotate_refresh(db: AsyncSession, refresh_token: str, now: datetime) -> SessionTokens:
    token = await db.get(RefreshToken, token_hash(refresh_token))
    if token is None:
        raise AppError(401, "INVALID_AUTH")
    initial = await db.get(Session, token.session_id)
    assert initial is not None
    # Common lock order: user -> session. Blocking and refresh cannot deadlock.
    user = await db.scalar(select(User).where(User.id == initial.user_id).with_for_update())
    family = await db.scalar(
        select(Session)
        .where(Session.id == token.session_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    await db.refresh(token)
    assert family is not None and user is not None
    if family.revoked or family.expires_at <= now or not user.is_active:
        raise AppError(401, "INVALID_AUTH")
    if token.spent:
        family.revoked = True
        await db.commit()  # reuse revocation must survive the rejected request
        raise AppError(401, "INVALID_AUTH")
    token.spent = True
    return await issue_tokens(db, family, now)


async def revoke_user_sessions(db: AsyncSession, user_id: UUID) -> None:
    await db.execute(update(Session).where(Session.user_id == user_id).values(revoked=True))
