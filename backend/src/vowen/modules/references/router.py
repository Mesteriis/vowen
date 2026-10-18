from fastapi import APIRouter
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from vowen.core.errors import AppError
from vowen.modules.auth.router import DB, Member
from vowen.modules.identity.administration import administrator
from vowen.modules.identity.models import AdministrationState
from vowen.modules.references.equipment import add_links, populate_links
from vowen.modules.references.fixtures import CATALOGUES, ReferenceKind
from vowen.modules.references.models import Practice, PracticeCategory
from vowen.modules.references.schemas import PracticeCreate, ReferenceView

router = APIRouter(prefix="/api/v1")


@router.get("/references/{kind}", response_model=list[ReferenceView])
async def entries(kind: ReferenceKind, principal: Member, db: DB) -> list[ReferenceView]:
    model = CATALOGUES[kind]
    rows = await db.scalars(select(model).order_by(model.name, model.uid))
    views = [ReferenceView.model_validate(row) for row in rows]
    return await populate_links(db, views) if kind == "practices" else views


@router.post("/administration/practices", response_model=ReferenceView, status_code=201)
async def add_practice(body: PracticeCreate, principal: Member, db: DB) -> ReferenceView:
    state = await db.get(AdministrationState, 1, with_for_update=True, populate_existing=True)
    if state is None:
        raise AppError(503, "UNAVAILABLE")
    await administrator(db, principal.user_id)
    if body.category_uid is not None and await db.get(PracticeCategory, body.category_uid) is None:
        raise AppError(422, "INVALID_PRACTICE_CATEGORY")
    entry = Practice(**body.model_dump(exclude={"device_uids", "body_part_uids"}))
    try:
        async with db.begin_nested():
            db.add(entry)
            await db.flush()
            await add_links(db, entry.uid, body.device_uids, body.body_part_uids)
    except IntegrityError:
        raise AppError(409, "REFERENCE_EXISTS") from None
    return (await populate_links(db, [ReferenceView.model_validate(entry)]))[0]
