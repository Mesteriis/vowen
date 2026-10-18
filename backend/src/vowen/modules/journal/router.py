from uuid import UUID, uuid4
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Query, Request, Response
from sqlalchemy import select

from vowen.core.errors import AppError
from vowen.modules.auth.router import DB, Member
from vowen.modules.identity.models import UserPreferences
from vowen.modules.journal import service as s
from vowen.modules.journal.models import JournalEntry, JournalReader
from vowen.modules.journal.schemas import JournalContent, JournalEdit, JournalView
from vowen.modules.relations.router import cipher_for
from vowen.modules.relations.schemas import ExpectedVersion

router = APIRouter(prefix="/api/v1/journal")


@router.get("", response_model=list[JournalView])
@router.get("/export", response_model=list[JournalView])
async def listing(
    principal: Member,
    db: DB,
    request: Request,
    search: str = Query(default="", max_length=200),
    tag: str = Query(default="", max_length=100),
) -> list[JournalView]:
    rows = (
        await db.scalars(
            select(JournalEntry)
            .where(
                (JournalEntry.author_id == principal.user_id)
                | (
                    JournalEntry.published
                    & JournalEntry.id.in_(
                        select(JournalReader.entry_id).where(
                            JournalReader.user_id == principal.user_id
                        )
                    )
                )
            )
            .order_by(JournalEntry.created_at, JournalEntry.id)
        )
    ).all()
    result = []
    for e in rows:
        # Author/reader checks happen before decrypting or counting any result.
        if not await s.visible(db, e, principal.user_id):
            continue
        v = await s.view(db, e, cipher_for(request))
        if search.casefold() not in (v.title + "\n" + v.text).casefold() or (
            tag and tag not in v.tags
        ):
            continue
        result.append(v)
    return result


@router.post("", response_model=JournalView)
async def create(body: JournalContent, principal: Member, db: DB, request: Request) -> JournalView:
    now = request.app.state.clock.now()
    prefs = await db.get(UserPreferences, principal.user_id)
    today = now.astimezone(ZoneInfo(prefs.timezone if prefs else "UTC")).date()
    if body.date != today:
        raise AppError(422, "JOURNAL_DATE_MUST_BE_TODAY")
    e = JournalEntry(
        id=uuid4(),
        author_id=principal.user_id,
        revision=1,
        visibility="private",
        published=False,
        created_at=now,
        updated_at=now,
    )
    s.seal(e, body, cipher_for(request))
    db.add(e)
    await db.flush()
    # A newly created all-current snapshot always captures the current audience.
    await s.audience(db, e, body, refresh=True)
    return await s.view(db, e, cipher_for(request))


@router.get("/{eid}", response_model=JournalView)
async def detail(eid: UUID, principal: Member, db: DB, request: Request) -> JournalView:
    return await s.view(db, await s.loaded(db, eid, principal.user_id), cipher_for(request))


@router.patch("/{eid}", response_model=JournalView)
async def edit(
    eid: UUID, body: JournalEdit, principal: Member, db: DB, request: Request
) -> JournalView:
    e = await s.loaded(db, eid, principal.user_id)
    if e.author_id != principal.user_id:
        raise AppError(403, "ACCESS_DENIED")
    if e.revision != body.expected_version:
        raise AppError(409, "VERSION_CONFLICT")
    previous = await s.view(db, e, cipher_for(request))
    if body.date != previous.date:
        raise AppError(422, "JOURNAL_DATE_IMMUTABLE")
    if "handwriting" not in body.model_fields_set:
        body = body.model_copy(update={"handwriting": previous.handwriting})
    await s.audience(db, e, body, body.refresh_audience)
    s.seal(e, body, cipher_for(request))
    e.revision += 1
    e.updated_at = request.app.state.clock.now()
    return await s.view(db, e, cipher_for(request))


@router.post("/{eid}/delete", status_code=204)
async def remove(eid: UUID, body: ExpectedVersion, principal: Member, db: DB) -> Response:
    e = await s.loaded(db, eid, principal.user_id)
    if e.author_id != principal.user_id:
        raise AppError(403, "ACCESS_DENIED")
    if e.revision != body.expected_version:
        raise AppError(409, "VERSION_CONFLICT")
    await db.delete(e)
    return Response(status_code=204)
