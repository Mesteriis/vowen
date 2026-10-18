from uuid import UUID

from fastapi import APIRouter, Query, Response

from vowen.core.errors import AppError
from vowen.modules.auth.router import DB, Member
from vowen.modules.participant_profiles import service as s
from vowen.modules.participant_profiles.models import ProfileDraft
from vowen.modules.participant_profiles.schemas import (
    ProfileDraftPatch,
    ProfileDraftView,
    ProfilePublish,
    ProfileView,
    SharedProfileView,
)

router = APIRouter(prefix="/api/v1")


@router.get("/me/profile", response_model=ProfileView)
async def own(principal: Member, db: DB) -> ProfileView:
    return await s.get_own_profile(db, principal.user_id)


@router.get("/me/profile/draft", response_model=ProfileDraftView)
async def draft(principal: Member, db: DB) -> ProfileDraftView:
    value = await db.get(ProfileDraft, principal.user_id)
    if value is None:
        raise AppError(404, "NOT_FOUND")
    return s.draft_view(value)


@router.put("/me/profile/draft", response_model=ProfileDraftView)
async def save(body: ProfileDraftPatch, principal: Member, db: DB) -> ProfileDraftView:
    return await s.save_draft(db, principal.user_id, body)


@router.delete("/me/profile/draft", status_code=204)
async def discard(principal: Member, db: DB, expected_version: int = Query(ge=1)) -> Response:
    await s.discard_draft(db, principal.user_id, expected_version)
    return Response(status_code=204)


@router.post("/me/profile/publish", response_model=ProfileView)
async def publish(body: ProfilePublish, principal: Member, db: DB) -> ProfileView:
    return await s.publish_draft(db, principal.user_id, body)


@router.get("/participants/{owner_id}/profile", response_model=SharedProfileView)
async def shared(owner_id: UUID, principal: Member, db: DB) -> SharedProfileView:
    return await s.read_shared_profile(db, principal.user_id, owner_id)
