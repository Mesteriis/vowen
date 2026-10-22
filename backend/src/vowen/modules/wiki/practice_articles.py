"""Explicit Russian practice articles, upgrading only pristine reference stubs."""

from datetime import UTC, datetime
from importlib.resources import files
from typing import Literal
from uuid import UUID, uuid5

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from vowen.core.errors import AppError
from vowen.modules.references.models import Practice, PracticeCategory, PracticeDevice
from vowen.modules.wiki.models import WikiPage, WikiSection
from vowen.modules.wiki.pages import add_revision
from vowen.modules.wiki.schemas import WikiDocument, WikiSource
from vowen.modules.wiki.sections import lock_wiki, validate_tree
from vowen.modules.wiki.seed import NAMESPACE, pristine_reference_page, reference_stub


class PracticeArticle(BaseModel):
    model_config = ConfigDict(extra="forbid")
    code: str = Field(pattern=r"^[a-z]+(?:-[a-z]+)*$")
    title: str = Field(min_length=1, max_length=160)
    summary: str = Field(min_length=1, max_length=600)
    body: str = Field(default="", max_length=100000)
    sources: list[WikiSource] = Field(default_factory=list, max_length=20)


class PracticeCorpus(BaseModel):
    model_config = ConfigDict(extra="forbid")
    language: Literal["ru"]
    version: Literal[1]
    articles: list[PracticeArticle]


class PracticeImportResult(BaseModel):
    created: int = 0
    updated: int = 0
    skipped: int = 0


def load_practice_articles() -> list[PracticeArticle]:
    root = files("vowen.modules.wiki").joinpath("fixtures", "ru", "practices-v1")
    corpus = PracticeCorpus.model_validate_json(root.joinpath("manifest.json").read_text("utf-8"))
    if len({a.code for a in corpus.articles}) != len(corpus.articles):
        raise ValueError("Duplicate practice article code")
    result = []
    for article in corpus.articles:
        body = root.joinpath("articles", article.code + ".md").read_text("utf-8")
        if not body.strip():
            raise ValueError("Empty practice article")
        result.append(PracticeArticle.model_validate({**article.model_dump(), "body": body}))
    return result


async def seed_practice_articles(db: AsyncSession, actor_id: UUID) -> PracticeImportResult:
    articles = load_practice_articles()
    tree = await lock_wiki(db, actor_id)
    references: dict[str, list[Practice]] = {}
    for reference in await db.scalars(select(Practice)):
        code = reference.extra.get("code")
        if isinstance(code, str):
            references.setdefault(code, []).append(reference)
    if any(len(references.get(a.code, [])) != 1 for a in articles):
        raise AppError(422, "INVALID_EDITORIAL_REFERENCE")

    result = PracticeImportResult()
    root_uid = uuid5(NAMESPACE, "practices")
    structure_changed = False
    if not await db.get(WikiSection, root_uid):
        db.add(WikiSection(uid=root_uid, title="Практики", sort_order=0))
        await db.flush()
        structure_changed = True
    selected_categories = {
        references[a.code][0].category_uid for a in articles
        if references[a.code][0].category_uid is not None
    }
    category_sections = {}
    for uid in selected_categories:
        category = await db.get(PracticeCategory, uid)
        if category is None:
            raise AppError(422, "INVALID_EDITORIAL_REFERENCE")
        section_uid = uuid5(NAMESPACE, "practices:category:" + str(uid))
        category_sections[uid] = section_uid
        if not await db.get(WikiSection, section_uid):
            db.add(WikiSection(
                uid=section_uid, parent_uid=root_uid, title=category.name,
                description=category.description[:600],
            ))
            structure_changed = True
    await db.flush()
    validate_tree({s.uid: s.parent_uid for s in await db.scalars(select(WikiSection))})

    for article in articles:
        reference = references[article.code][0]
        section_uid = category_sections.get(reference.category_uid, root_uid)
        stub = reference_stub(reference, section_uid)
        page = await db.scalar(select(WikiPage).where(
            WikiPage.practice_uid == reference.uid,
        ).with_for_update())
        is_new = page is None
        if page is not None and not await pristine_reference_page(
            db, page, reference, "practices", section_uid
        ):
            result.skipped += 1
            continue
        devices = list(await db.scalars(
            select(PracticeDevice.device_uid)
            .where(PracticeDevice.practice_uid == reference.uid)
            .order_by(PracticeDevice.device_uid)
        ))
        document = WikiDocument.model_validate({
            **stub.model_dump(),
            "summary": article.summary,
            "body": article.body,
            "device_uids": devices,
            "sources": [s.model_dump() for s in stub.sources + article.sources],
        })
        if page is None:
            page = WikiPage(
                uid=uuid5(NAMESPACE, "practices:" + str(reference.uid)),
                kind="encyclopedia", practice_uid=reference.uid,
            )
            db.add(page)
            await db.flush()
        revision = await add_revision(db, actor_id, page, document)
        revision.published_at = datetime.now(UTC)
        page.published_revision_uid = revision.uid
        if is_new:
            result.created += 1
        else:
            page.version += 1
            result.updated += 1
    if result.created or result.updated or structure_changed:
        tree.version += 1
    await db.flush()
    return result
