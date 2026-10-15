import re
import secrets
from datetime import datetime, timedelta
from uuid import UUID, uuid4

from pydantic import Field
from sqlalchemy import DateTime, ForeignKey, String, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from vowen.core.database import Base
from vowen.core.errors import AppError
from vowen.modules.auth.schemas import Input, SessionTokens
from vowen.modules.auth.service import active_user, create_session, token_hash
from vowen.modules.identity.models import User


class AndroidChallenge(Base):
    __tablename__ = "android_login_challenges"
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    start_token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    poll_secret_hash: Mapped[str] = mapped_column(String(64), unique=True)
    nonce_hash: Mapped[str] = mapped_column(String(64))
    device_label: Mapped[str] = mapped_column(String(100))
    display_code: Mapped[str] = mapped_column(String(6))
    status: Mapped[str] = mapped_column(String(20), default="pending")
    user_id: Mapped[UUID | None] = mapped_column(ForeignKey("users.id"))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class ChallengeRequest(Input):
    client_nonce: str = Field(pattern=r"^[A-Za-z0-9_-]{43}$")
    device_label: str = Field(min_length=1, max_length=100)


class ChallengeProof(Input):
    poll_secret: str = Field(min_length=43, max_length=43)
    client_nonce: str = Field(min_length=43, max_length=43)


class ChallengeCreated(Input):
    challenge_id: UUID
    bot_url: str
    poll_secret: str
    display_code: str
    expires_at: datetime


class ChallengeStatus(Input):
    status: str


async def create_challenge(
    db: AsyncSession, client_nonce: str, device_label: str, bot_username: str, now: datetime
) -> ChallengeCreated:
    if not re.fullmatch(r"[A-Za-z0-9_]{5,32}", bot_username):
        raise AppError(503, "UNAVAILABLE")
    start, poll = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
    challenge = AndroidChallenge(
        start_token_hash=token_hash(start),
        poll_secret_hash=token_hash(poll),
        nonce_hash=token_hash(client_nonce),
        device_label=device_label,
        display_code=f"{secrets.randbelow(1000000):06d}",
        expires_at=now + timedelta(seconds=300),
    )
    db.add(challenge)
    await db.flush()
    return ChallengeCreated(
        challenge_id=challenge.id,
        bot_url=f"https://t.me/{bot_username}?start=login_{start}",
        poll_secret=poll,
        display_code=challenge.display_code,
        expires_at=challenge.expires_at,
    )


async def present_challenge(
    db: AsyncSession, start_token: str, telegram_actor_id: int, now: datetime
) -> AndroidChallenge:
    user = await active_user(db, telegram_actor_id)
    challenge = await db.scalar(
        select(AndroidChallenge)
        .where(AndroidChallenge.start_token_hash == token_hash(start_token))
        .with_for_update()
    )
    if challenge is None or challenge.expires_at <= now or challenge.status != "pending":
        raise AppError(401, "INVALID_AUTH")
    if challenge.user_id is not None and challenge.user_id != user.id:
        raise AppError(403, "ACCESS_DENIED")
    challenge.user_id = user.id
    return challenge


async def decide_challenge(
    db: AsyncSession, challenge_id: UUID, telegram_actor_id: int, approve: bool, now: datetime
) -> None:
    user = await active_user(db, telegram_actor_id)
    challenge = await db.scalar(
        select(AndroidChallenge).where(AndroidChallenge.id == challenge_id).with_for_update()
    )
    if challenge is None or challenge.user_id != user.id or challenge.expires_at <= now:
        raise AppError(403, "ACCESS_DENIED")
    decision = "approved" if approve else "rejected"
    if challenge.status == decision:
        return
    if challenge.status != "pending":
        raise AppError(409, "CONFLICT")
    challenge.status = decision


async def check_proof(
    db: AsyncSession,
    challenge_id: UUID,
    poll_secret: str,
    client_nonce: str,
    now: datetime,
    lock: bool = False,
) -> AndroidChallenge:
    query = select(AndroidChallenge).where(AndroidChallenge.id == challenge_id)
    if lock:
        query = query.with_for_update().execution_options(populate_existing=True)
    challenge = await db.scalar(query)
    if (
        challenge is None
        or not secrets.compare_digest(challenge.poll_secret_hash, token_hash(poll_secret))
        or not secrets.compare_digest(challenge.nonce_hash, token_hash(client_nonce))
    ):
        raise AppError(401, "INVALID_AUTH")
    if challenge.expires_at <= now:
        raise AppError(401, "INVALID_AUTH")
    return challenge


async def consume_challenge(
    db: AsyncSession, challenge_id: UUID, poll_secret: str, client_nonce: str, now: datetime
) -> SessionTokens:
    initial = await check_proof(db, challenge_id, poll_secret, client_nonce, now)
    if initial.user_id is None:
        raise AppError(409, "CONFLICT")
    user = await db.scalar(select(User).where(User.id == initial.user_id).with_for_update())
    challenge = await check_proof(db, challenge_id, poll_secret, client_nonce, now, lock=True)
    if user is None or not user.is_active:
        raise AppError(403, "ACCESS_DENIED")
    if challenge.status != "approved":
        raise AppError(409, "CONFLICT")
    challenge.status = "consumed"
    return await create_session(db, user, "android", challenge.device_label, now)
