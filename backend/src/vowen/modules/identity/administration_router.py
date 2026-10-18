from uuid import UUID

from fastapi import APIRouter, Request, Response

from vowen.modules.auth.router import DB, Member
from vowen.modules.identity.administration import (
    AdministrationCommand,
    AdministrationView,
    administration_view,
    change_administrator,
)

router = APIRouter(prefix="/api/v1/administration")


@router.get("", response_model=AdministrationView)
async def view(principal: Member, db: DB) -> AdministrationView:
    return await administration_view(db, principal.user_id)


@router.post("/administrators/{user_id}/grant", status_code=204)
async def grant(
    user_id: UUID, body: AdministrationCommand, principal: Member, db: DB, request: Request
) -> Response:
    await change_administrator(
        db,
        principal.user_id,
        user_id,
        "grant",
        body.expected_revision,
        request.app.state.clock.now(),
    )
    return Response(status_code=204)


@router.post("/administrators/{user_id}/transfer", status_code=204)
async def transfer(
    user_id: UUID, body: AdministrationCommand, principal: Member, db: DB, request: Request
) -> Response:
    await change_administrator(
        db,
        principal.user_id,
        user_id,
        "transfer",
        body.expected_revision,
        request.app.state.clock.now(),
    )
    return Response(status_code=204)
