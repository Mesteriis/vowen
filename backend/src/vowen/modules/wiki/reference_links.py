"""Reader-visible reference mappings; never advertise unpublished or archived pages."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from vowen.modules.references.fixtures import CATALOGUES, ReferenceKind
from vowen.modules.wiki.catalogue_articles import catalogue_page_uid
from vowen.modules.wiki.models import WikiPage, WikiRevision
from vowen.modules.wiki.schemas import WikiReferenceLink


async def reference_links(db: AsyncSession, kind: ReferenceKind) -> list[WikiReferenceLink]:
    model = CATALOGUES[kind]
    main = {
        "practices": WikiPage.practice_uid, "poses": WikiPage.pose_uid,
        "devices": WikiPage.device_uid,
    }.get(kind)
    if main is not None:
        # Include user-created encyclopedic pages rather than deriving their UUID on clients.
        rows = (await db.execute(
            select(model.uid, WikiPage.uid).join(WikiPage, main == model.uid)
            .join(WikiRevision, WikiRevision.uid == WikiPage.published_revision_uid)
            .where(WikiPage.archived_at.is_(None), WikiPage.kind == "encyclopedia")
            .order_by(model.uid, WikiPage.uid)
        )).all()
        return [WikiReferenceLink(reference_uid=r, page_uid=p) for r, p in rows]
    references = list(await db.scalars(select(model.uid).order_by(model.uid)))
    if not references:
        return []
    canonical = {catalogue_page_uid(kind, uid): uid for uid in references}
    pages = await db.scalars(
        select(WikiPage.uid)
        .join(WikiRevision, WikiRevision.uid == WikiPage.published_revision_uid)
        .where(
            WikiPage.uid.in_(canonical), WikiPage.kind == "article",
            WikiPage.archived_at.is_(None), WikiPage.practice_uid.is_(None),
            WikiPage.pose_uid.is_(None), WikiPage.device_uid.is_(None),
        )
    )
    return [WikiReferenceLink(reference_uid=canonical[p], page_uid=p) for p in sorted(pages)]
