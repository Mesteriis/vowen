from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from vowen.core.errors import AppError
from vowen.modules.auth.schemas import MemberView
from vowen.modules.identity.models import User, UserPreferences
from vowen.modules.identity.schemas import ProfilePatch


async def profile_view(db: AsyncSession, user: User) -> MemberView:
    preferences = await db.get(UserPreferences, user.id)
    if preferences is None:
        raise AppError(503, "UNAVAILABLE")
    return MemberView(
        id=user.id,
        display_name=user.display_name,
        paused=user.paused,
        language=preferences.language,
        timezone=preferences.timezone,
        profile_labels=preferences.profile_labels,
        profile_version=preferences.profile_version,
    )


async def update_profile(db: AsyncSession, user_id: UUID, patch: ProfilePatch) -> MemberView:
    user = await db.scalar(select(User).where(User.id == user_id).with_for_update())
    if user is None or not user.is_active:
        raise AppError(401, "INVALID_AUTH")
    preferences = await db.get(UserPreferences, user_id, with_for_update=True)
    if preferences is None:
        raise AppError(503, "UNAVAILABLE")
    if preferences.profile_version != patch.expected_version:
        raise AppError(409, "CONFLICT")
    if patch.display_name is not None:
        user.display_name = patch.display_name
    if patch.language is not None:
        preferences.language = patch.language
    if patch.timezone is not None:
        preferences.timezone = patch.timezone
    if patch.profile_labels is not None:
        preferences.profile_labels = list(patch.profile_labels)
    preferences.profile_version += 1
    await db.flush()
    return await profile_view(db, user)
