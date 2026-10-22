"""Missing-only Wiki publications for reference catalogues beyond the initial three."""

import json
from datetime import UTC, datetime
from importlib.resources import files
from uuid import UUID, uuid5

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from vowen.core.errors import AppError
from vowen.modules.references.fixtures import CATALOGUES, ReferenceKind
from vowen.modules.references.models import ReferenceEntry
from vowen.modules.wiki.models import WikiPage, WikiSection
from vowen.modules.wiki.pages import add_revision
from vowen.modules.wiki.queries import publication
from vowen.modules.wiki.schemas import WikiDocument, WikiSeedResult, WikiSource
from vowen.modules.wiki.sections import lock_wiki, validate_tree
from vowen.modules.wiki.seed import NAMESPACE, reference_stub

CATALOGUE_TITLES: dict[ReferenceKind, str] = {
    "biological-sex": "Половые характеристики", "genders": "Гендер",
    "practice-categories": "Категории практик", "practices": "Практики",
    "pose-categories": "Категории поз", "poses": "Позы", "devices": "Девайсы",
    "body-parts": "Части тела", "materials": "Материалы",
    "role-scenarios": "Ролевые сценарии", "interaction-formats": "Форматы взаимодействия",
    "venues": "Места", "health-conditions": "Состояния здоровья", "allergens": "Аллергены",
    "participant-compositions": "Составы участников", "timezones": "Часовые пояса",
    "relationship-types": "Виды отношений",
}


class ReferencePointer(BaseModel):
    model_config = ConfigDict(extra="forbid")
    kind: ReferenceKind
    uid: UUID


class CatalogueArticle(BaseModel):
    model_config = ConfigDict(extra="forbid")
    reference: ReferencePointer
    summary: str = Field(min_length=1, max_length=600)
    body: str = Field(default="", max_length=90000)
    sources: list[WikiSource] = Field(min_length=1, max_length=20)
    related_references: list[ReferencePointer] = Field(min_length=1, max_length=30)
    related_pages: list[UUID] = Field(default_factory=list, max_length=30)


def catalogue_page_uid(kind: ReferenceKind, uid: UUID) -> UUID:
    key = kind + ":" + str(uid) if kind in {"practices", "devices", "poses"} else (
        "catalogue:" + kind + ":" + str(uid)
    )
    return uuid5(NAMESPACE, key)


def load_catalogue_articles() -> list[CatalogueArticle]:
    root = files("vowen.modules.wiki").joinpath("fixtures", "ru", "catalogues-v1")
    payload = json.loads(root.joinpath("manifest.json").read_text("utf-8"))
    if payload.get("version") != 1 or payload.get("language") != "ru":
        raise ValueError("Unsupported catalogue corpus")
    articles = [CatalogueArticle.model_validate(a) for a in payload["articles"]]
    if len({(a.reference.kind, a.reference.uid) for a in articles}) != len(articles):
        raise ValueError("Duplicate reference article")
    for article in articles:
        if article.reference.kind in {"practices", "poses", "devices"}:
            raise ValueError("Use the existing domain article importer")
        path = root.joinpath("articles", article.reference.uid.hex + ".md")
        body = path.read_text("utf-8")
        if not body.strip():
            raise ValueError("Empty reference article")
        article.body = CatalogueArticle.model_validate({**article.model_dump(), "body": body}).body
    return articles


def markdown_label(value: str) -> str:
    return value.replace("\\", "\\\\").replace("[", "\\[").replace("]", "\\]")


async def seed_catalogue_articles(db: AsyncSession, actor_id: UUID) -> WikiSeedResult:
    articles = load_catalogue_articles()
    tree = await lock_wiki(db, actor_id)
    references: dict[tuple[ReferenceKind, UUID], ReferenceEntry] = {}
    for article in articles:
        for pointer in [article.reference, *article.related_references]:
            key = (pointer.kind, pointer.uid)
            if key not in references:
                reference = await db.get(CATALOGUES[pointer.kind], pointer.uid)
                if reference is None:
                    raise AppError(422, "INVALID_EDITORIAL_REFERENCE")
                references[key] = reference
    published = {p.uid: r.title for p, r in (await db.execute(publication())).all()}
    current = {
        catalogue_page_uid(a.reference.kind, a.reference.uid): a for a in articles
    }
    pending = {uid for uid in current if await db.get(WikiPage, uid) is None}
    targets = published | {
        uid: references[(a.reference.kind, a.reference.uid)].name for uid, a in current.items()
        if uid in pending
    }
    # An archived/draft-only target must not become a public link merely by being in this corpus.
    for article in articles:
        if catalogue_page_uid(article.reference.kind, article.reference.uid) not in pending:
            continue
        for pointer in article.related_references:
            if catalogue_page_uid(pointer.kind, pointer.uid) not in targets:
                raise AppError(422, "INVALID_WIKI_LINK")
        if any(uid not in targets for uid in article.related_pages):
            raise AppError(422, "INVALID_WIKI_LINK")

    root_uid = uuid5(NAMESPACE, "catalogues")
    changed = False
    if not await db.get(WikiSection, root_uid):
        db.add(WikiSection(uid=root_uid, title="Справочники", sort_order=4))
        await db.flush()
        changed = True
    sections = {}
    for kind in dict.fromkeys(a.reference.kind for a in articles):
        uid = uuid5(NAMESPACE, "catalogue-section:" + kind)
        sections[kind] = uid
        if not await db.get(WikiSection, uid):
            db.add(WikiSection(uid=uid, parent_uid=root_uid, title=CATALOGUE_TITLES[kind]))
            changed = True
    await db.flush()
    validate_tree({s.uid: s.parent_uid for s in await db.scalars(select(WikiSection))})
    created, skipped = 0, 0
    for uid, article in current.items():
        if await db.get(WikiPage, uid):
            skipped += 1
            continue
        pointer = article.reference
        reference = references[(pointer.kind, pointer.uid)]
        related = {
            catalogue_page_uid(p.kind, p.uid) for p in article.related_references
        } | set(article.related_pages)
        related.discard(uid)
        links = [
            f"- [{markdown_label(targets[target])}](#wiki?page={target})"
            for target in sorted(related, key=str)
        ]
        body = article.body.rstrip() + "\n\n## Связанные материалы\n\n" + "\n".join(links) + "\n"
        stub = reference_stub(reference, sections[pointer.kind])
        document = WikiDocument(
            section_uid=sections[pointer.kind], title=reference.name[:160],
            summary=article.summary, body=body, thumbnail=stub.thumbnail, sources=article.sources,
        )
        page = WikiPage(uid=uid, kind="article")
        db.add(page)
        await db.flush()
        revision = await add_revision(db, actor_id, page, document)
        revision.published_at = datetime.now(UTC)
        page.published_revision_uid = revision.uid
        created += 1
    if changed or created:
        tree.version += 1
    await db.flush()
    return WikiSeedResult(created=created, skipped=skipped)
