from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Query
from sqlalchemy import select

from vowen.core.errors import AppError
from vowen.modules.auth.router import DB, Member
from vowen.modules.identity.administration import administrator
from vowen.modules.references.fixtures import ReferenceKind
from vowen.modules.wiki.models import WikiPage, WikiRevision
from vowen.modules.wiki.pages import (
    create_page,
    edit_view,
    publish_page,
    revision_view,
    save_page,
    set_archived,
)
from vowen.modules.wiki.queries import published_page, search_pages, wiki_tree
from vowen.modules.wiki.reference_links import reference_links
from vowen.modules.wiki.schemas import (
    WikiArchive,
    WikiEditView,
    WikiPageCreate,
    WikiPageSave,
    WikiPageView,
    WikiPublish,
    WikiReferenceLink,
    WikiRevisionView,
    WikiSearchView,
    WikiSectionSave,
    WikiSeedResult,
    WikiTreeView,
)
from vowen.modules.wiki.sections import delete_section, save_section
from vowen.modules.wiki.seed import seed_reference_pages

router = APIRouter(prefix="/api/v1/wiki", tags=["wiki"])


@router.get("/tree")
async def tree(db: DB, actor: Member) -> WikiTreeView:
    return await wiki_tree(db)


@router.get("/search")
async def search(
    db: DB,
    actor: Member,
    q: str = Query(default="", max_length=200),
    section_uid: UUID | None = None,
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=50),
) -> WikiSearchView:
    return await search_pages(db, q, section_uid, offset, limit)


@router.get("/reference-links/{kind}")
async def references(kind: ReferenceKind, db: DB, actor: Member) -> list[WikiReferenceLink]:
    return await reference_links(db, kind)


@router.get("/pages/{uid}")
async def page(uid: UUID, db: DB, actor: Member) -> WikiPageView:
    return await published_page(db, uid)


# Separate endpoints prevent a reader-selected mode from exposing draft fields.


@router.post("/admin/pages")
async def create(command: WikiPageCreate, db: DB, actor: Member) -> WikiEditView:
    return await create_page(db, actor.user_id, command)


@router.get("/admin/pages")
async def drafts(
    db: DB,
    actor: Member,
    state: Literal["drafts", "published", "archived"] = "drafts",
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=50),
) -> list[WikiEditView]:
    await administrator(db, actor.user_id)
    query = select(WikiPage)
    if state == "archived":
        query = query.where(WikiPage.archived_at.is_not(None))
    elif state == "published":
        query = query.where(
            WikiPage.archived_at.is_(None), WikiPage.published_revision_uid.is_not(None)
        )
    else:
        query = query.where(
            WikiPage.archived_at.is_(None),
            WikiPage.published_revision_uid.is_distinct_from(WikiPage.draft_revision_uid),
        )
    pages = await db.scalars(query.order_by(WikiPage.uid).offset(offset).limit(limit))
    return [await edit_view(db, page) for page in pages]


@router.get("/admin/pages/{uid}")
async def edit(uid: UUID, db: DB, actor: Member) -> WikiEditView:
    await administrator(db, actor.user_id)
    page = await db.get(WikiPage, uid)
    if page is None:
        raise AppError(404, "NOT_FOUND")
    return await edit_view(db, page)


@router.patch("/admin/pages/{uid}")
async def save(uid: UUID, command: WikiPageSave, db: DB, actor: Member) -> WikiEditView:
    return await save_page(db, actor.user_id, uid, command)


@router.post("/admin/pages/{uid}/publish")
async def publish(uid: UUID, command: WikiPublish, db: DB, actor: Member) -> WikiEditView:
    return await publish_page(db, actor.user_id, uid, command)


@router.post("/admin/pages/{uid}/archive")
async def archive(uid: UUID, command: WikiArchive, db: DB, actor: Member) -> WikiEditView:
    return await set_archived(db, actor.user_id, uid, command)


@router.get("/admin/pages/{uid}/revisions")
async def history(
    uid: UUID,
    db: DB,
    actor: Member,
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=50),
) -> list[WikiRevisionView]:
    await administrator(db, actor.user_id)
    if not await db.get(WikiPage, uid):
        raise AppError(404, "NOT_FOUND")
    rows = await db.scalars(
        select(WikiRevision)
        .where(WikiRevision.page_uid == uid)
        .order_by(WikiRevision.created_at.desc(), WikiRevision.uid)
        .offset(offset)
        .limit(limit)
    )
    return [await revision_view(db, revision) for revision in rows]


@router.get("/admin/pages/{uid}/revisions/{revision_uid}")
async def old_revision(uid: UUID, revision_uid: UUID, db: DB, actor: Member) -> WikiRevisionView:
    await administrator(db, actor.user_id)
    revision = await db.get(WikiRevision, revision_uid)
    if revision is None or revision.page_uid != uid:
        raise AppError(404, "NOT_FOUND")
    return await revision_view(db, revision)


@router.post("/admin/sections")
async def create_section(command: WikiSectionSave, db: DB, actor: Member) -> WikiTreeView:
    return await save_section(db, actor.user_id, None, command)


@router.patch("/admin/sections/{uid}")
async def update_section(
    uid: UUID, command: WikiSectionSave, db: DB, actor: Member
) -> WikiTreeView:
    return await save_section(db, actor.user_id, uid, command)


@router.delete("/admin/sections/{uid}")
async def remove_section(
    uid: UUID,
    db: DB,
    actor: Member,
    expected_version: int = Query(ge=1),
    expected_tree_version: int = Query(ge=1),
) -> WikiTreeView:
    return await delete_section(db, actor.user_id, uid, expected_version, expected_tree_version)


@router.post("/admin/seed-references")
async def seed(db: DB, actor: Member) -> WikiSeedResult:
    return await seed_reference_pages(db, actor.user_id)
