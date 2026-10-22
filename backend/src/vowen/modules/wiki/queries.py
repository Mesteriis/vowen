from uuid import UUID

from sqlalchemy import Select, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from vowen.core.errors import AppError
from vowen.modules.wiki.models import (
    WikiPage,
    WikiRevision,
    WikiRevisionDevice,
    WikiRevisionPose,
    WikiRevisionPractice,
    WikiSection,
    WikiTreeState,
)
from vowen.modules.wiki.schemas import (
    WikiDocument,
    WikiPageSummary,
    WikiPageView,
    WikiSearchView,
    WikiSectionView,
    WikiSource,
    WikiTreeView,
)


def publication() -> Select[tuple[WikiPage, WikiRevision]]:
    return (
        select(WikiPage, WikiRevision)
        .join(WikiRevision, WikiPage.published_revision_uid == WikiRevision.uid)
        .where(WikiPage.archived_at.is_(None))
    )


def summary(page: WikiPage, revision: WikiRevision) -> WikiPageSummary:
    return WikiPageSummary(
        uid=page.uid,
        kind=page.kind,
        title=revision.title,
        summary=revision.summary,
        section_uid=revision.section_uid,
        thumbnail=revision.thumbnail,
        published_at=revision.published_at,
    )


async def revision_document(db: AsyncSession, revision: WikiRevision) -> WikiDocument:
    practices = list(
        await db.scalars(
            select(WikiRevisionPractice.practice_uid).where(
                WikiRevisionPractice.revision_uid == revision.uid
            )
        )
    )
    poses = list(
        await db.scalars(
            select(WikiRevisionPose.pose_uid).where(WikiRevisionPose.revision_uid == revision.uid)
        )
    )
    devices = list(
        await db.scalars(
            select(WikiRevisionDevice.device_uid).where(
                WikiRevisionDevice.revision_uid == revision.uid
            )
        )
    )
    return WikiDocument(
        section_uid=revision.section_uid,
        title=revision.title,
        summary=revision.summary,
        body=revision.body,
        thumbnail=revision.thumbnail,
        practice_uids=practices,
        pose_uids=poses,
        device_uids=devices,
        sources=[WikiSource.model_validate(s) for s in revision.sources],
    )


async def published_page(db: AsyncSession, uid: UUID) -> WikiPageView:
    row = (await db.execute(publication().where(WikiPage.uid == uid))).first()
    if row is None:
        raise AppError(404, "NOT_FOUND")
    page, revision = row
    document = await revision_document(db, revision)
    related_conditions = []
    for model, field, values, main in [
        (
            WikiRevisionPractice,
            WikiRevisionPractice.practice_uid,
            document.practice_uids,
            page.practice_uid,
        ),
        (WikiRevisionPose, WikiRevisionPose.pose_uid, document.pose_uids, page.pose_uid),
        (WikiRevisionDevice, WikiRevisionDevice.device_uid, document.device_uids, page.device_uid),
    ]:
        ids = set(values) | ({main} if main else set())
        if ids:
            related_conditions.append(
                WikiRevision.uid.in_(select(getattr(model, "revision_uid")).where(field.in_(ids)))
            )
            main_field = {
                WikiRevisionPractice: WikiPage.practice_uid,
                WikiRevisionPose: WikiPage.pose_uid,
                WikiRevisionDevice: WikiPage.device_uid,
            }[model]
            related_conditions.append(main_field.in_(ids))
    related = []
    if related_conditions:
        related = [
            summary(p, r)
            for p, r in (
                await db.execute(
                    publication()
                    .where(WikiPage.uid != uid, or_(*related_conditions))
                    .order_by(WikiPage.uid)
                    .limit(20)
                )
            ).all()
        ]
    return WikiPageView(
        uid=page.uid,
        kind=page.kind,
        practice_uid=page.practice_uid,
        pose_uid=page.pose_uid,
        device_uid=page.device_uid,
        revision_uid=revision.uid,
        document=document,
        author_id=revision.author_id,
        created_at=revision.created_at,
        published_at=revision.published_at,
        related_pages=related,
    )


async def wiki_tree(db: AsyncSession) -> WikiTreeView:
    state = await db.get(WikiTreeState, 1)
    if state is None:
        raise AppError(503, "UNAVAILABLE")
    sections = list(
        await db.scalars(select(WikiSection).order_by(WikiSection.sort_order, WikiSection.uid))
    )
    pages = [
        summary(p, r)
        for p, r in (
            await db.execute(publication().order_by(WikiRevision.title, WikiPage.uid))
        ).all()
    ]
    return WikiTreeView(
        version=state.version,
        sections=[WikiSectionView.model_validate(s) for s in sections],
        pages=pages,
    )


async def search_pages(
    db: AsyncSession, q: str, section_uid: UUID | None, offset: int, limit: int
) -> WikiSearchView:
    # The literal match deliberately does not interpret user SQL wildcards.
    query = publication()
    if q.strip():
        query = query.where(
            or_(
                *[
                    field.icontains(q.strip(), autoescape=True)
                    for field in [WikiRevision.title, WikiRevision.summary, WikiRevision.body]
                ]
            )
        )
    if section_uid:
        sections = list(await db.scalars(select(WikiSection)))
        included = {section_uid}
        for _ in range(8):
            included |= {s.uid for s in sections if s.parent_uid in included}
        query = query.where(WikiRevision.section_uid.in_(included))
    from sqlalchemy import func

    total = await db.scalar(select(func.count()).select_from(query.subquery())) or 0
    rows = (
        await db.execute(
            query.order_by(WikiRevision.title, WikiPage.uid).offset(offset).limit(limit)
        )
    ).all()
    return WikiSearchView(
        items=[summary(p, r) for p, r in rows], total=total, offset=offset, limit=limit
    )
