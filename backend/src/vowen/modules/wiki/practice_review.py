"""Explicit review of previously imported practice articles; preserve editor revisions."""

import hashlib
import json
from datetime import UTC, datetime
from importlib.resources import files
from uuid import UUID, uuid5

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from vowen.core.errors import AppError
from vowen.modules.references.fixtures import fixture_rows
from vowen.modules.references.models import Practice, PracticeDevice
from vowen.modules.wiki.catalogue_articles import markdown_label
from vowen.modules.wiki.editorial import editorial_uid, load_editorial
from vowen.modules.wiki.models import WikiPage, WikiRevision
from vowen.modules.wiki.pages import add_revision
from vowen.modules.wiki.practice_articles import PracticeArticle, load_practice_articles
from vowen.modules.wiki.queries import publication, revision_document
from vowen.modules.wiki.schemas import WikiDocument, WikiSource
from vowen.modules.wiki.sections import lock_wiki
from vowen.modules.wiki.seed import NAMESPACE, reference_stub


class PracticeReview(BaseModel):
    model_config = ConfigDict(extra="forbid")
    code: str
    baseline: PracticeArticle
    body_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    sources: list[WikiSource] = Field(min_length=1, max_length=20)
    scope: str = Field(min_length=1, max_length=2000)
    related_practice_codes: list[str] = Field(min_length=1, max_length=20)
    related_pages: list[UUID] = Field(default_factory=list, max_length=20)


class PracticeReviewResult(BaseModel):
    updated: int = 0
    skipped: int = 0


def load_practice_reviews() -> list[PracticeReview]:
    root = files("vowen.modules.wiki").joinpath("fixtures", "ru", "practice-reviews-v1")
    payload = json.loads(root.joinpath("manifest.json").read_text("utf-8"))
    if payload.get("version") != 1 or payload.get("language") != "ru":
        raise ValueError("Unsupported practice review corpus")
    reviews = [PracticeReview.model_validate(r) for r in payload["reviews"]]
    originals = {a.code: a for a in load_practice_articles()}
    if len({r.code for r in reviews}) != len(reviews):
        raise ValueError("Duplicate practice review")
    for review in reviews:
        original = originals.get(review.code)
        if (
            original is None or review.baseline.code != review.code
            or original.model_dump(exclude={"body"}) != review.baseline.model_dump(exclude={"body"})
            or hashlib.sha256(original.body.encode()).hexdigest() != review.body_sha256
        ):
            raise ValueError("Practice review baseline changed")
        if (
            review.code in review.related_practice_codes
            or len(set(review.related_practice_codes)) != len(review.related_practice_codes)
            or not set(review.related_practice_codes) <= originals.keys()
        ):
            raise ValueError("Invalid practice review links")
    return reviews


def render_review(
    original: PracticeArticle, review: PracticeReview, links: dict[UUID, str],
) -> PracticeArticle:
    source_links = "; ".join(
        f"[{markdown_label(s.name or 'Источник')}]({s.url})" for s in review.sources
    )
    body = original.body.rstrip() + "\n\n## Источники и область подтверждения\n\n"
    body += review.scope + "\n\n" + source_links + ".\n\n## Связанные материалы\n\n"
    body += "\n".join(
        f"- [{markdown_label(title)}](#wiki?page={uid})"
        for uid, title in sorted(links.items(), key=lambda pair: pair[1].casefold())
    ) + "\n"
    return original.model_copy(update={"body": body, "sources": review.sources})


def load_reviewed_practice_articles() -> list[PracticeArticle]:
    """Resolved delivery corpus; the original corpus remains a historical baseline."""
    reviews = {r.code: r for r in load_practice_reviews()}
    references = {r["extra"]["code"]: r for r in fixture_rows("practices")}
    editorial = {editorial_uid("article:" + a.key): a.title for a in load_editorial().articles}
    result = []
    for original in load_practice_articles():
        review = reviews.get(original.code)
        if review is None:
            result.append(original)
            continue
        links = {
            uuid5(NAMESPACE, "practices:" + str(references[code]["uid"])): references[code]["name"]
            for code in review.related_practice_codes
        }
        for uid in review.related_pages:
            if uid not in editorial:
                raise ValueError("Unknown practice editorial link")
            links[uid] = editorial[uid]
        result.append(render_review(original, review, links))
    return result


async def refresh_practice_pages(db: AsyncSession, actor_id: UUID) -> PracticeReviewResult:
    tree = await lock_wiki(db, actor_id)
    originals = {a.code: a for a in load_practice_articles()}
    reviews = load_practice_reviews()
    references: dict[str, list[Practice]] = {}
    for reference in await db.scalars(select(Practice)):
        code = reference.extra.get("code")
        if isinstance(code, str):
            references.setdefault(code, []).append(reference)
    required = {c for r in reviews for c in [r.code, *r.related_practice_codes]}
    if any(len(references.get(c, [])) != 1 for c in required):
        raise AppError(422, "INVALID_EDITORIAL_REFERENCE")
    published = {p.uid: r.title for p, r in (await db.execute(publication())).all()}
    result = PracticeReviewResult()
    for review in reviews:
        reference = references[review.code][0]
        uid = uuid5(NAMESPACE, "practices:" + str(reference.uid))
        page = await db.scalar(select(WikiPage).where(WikiPage.uid == uid).with_for_update())
        # Only a direct original import or its canonical stub -> original upgrade is eligible.
        if (
            page is None or page.kind != "encyclopedia" or page.practice_uid != reference.uid
            or page.archived_at is not None or page.version not in {1, 2}
            or page.published_revision_uid is None
            or page.draft_revision_uid != page.published_revision_uid
        ):
            result.skipped += 1
            continue
        revisions = list(await db.scalars(select(WikiRevision).where(
            WikiRevision.page_uid == page.uid,
        )))
        published_revision = next(
            (r for r in revisions if r.uid == page.published_revision_uid), None,
        )
        if len(revisions) != page.version or published_revision is None:
            result.skipped += 1
            continue
        section_uid = uuid5(NAMESPACE, "practices:category:" + str(reference.category_uid)) if (
            reference.category_uid is not None
        ) else uuid5(NAMESPACE, "practices")
        stub = reference_stub(reference, section_uid)
        prior = [r for r in revisions if r.uid != page.published_revision_uid]
        if prior and await revision_document(db, prior[0]) != stub:
            result.skipped += 1
            continue
        current = await revision_document(db, published_revision)
        devices = list(await db.scalars(select(PracticeDevice.device_uid).where(
            PracticeDevice.practice_uid == reference.uid,
        )))
        expected = WikiDocument.model_validate({
            **stub.model_dump(), "summary": review.baseline.summary, "body": "",
            "device_uids": devices, "sources": [s.model_dump() for s in (
                stub.sources + review.baseline.sources
            )],
        })
        related = {"practice_uids", "pose_uids", "device_uids"}
        ignored = related | {"body"}
        if (
            hashlib.sha256(current.body.encode()).hexdigest() != review.body_sha256
            or current.model_dump(exclude=ignored) != expected.model_dump(exclude=ignored)
            or any(set(getattr(current, k)) != set(getattr(expected, k)) for k in related)
        ):
            result.skipped += 1
            continue
        targets = {
            uuid5(NAMESPACE, "practices:" + str(references[c][0].uid))
            for c in review.related_practice_codes
        } | set(review.related_pages)
        if not targets <= published.keys():
            raise AppError(422, "INVALID_WIKI_LINK")
        updated = render_review(originals[review.code], review, {t: published[t] for t in targets})
        document = current.model_copy(update={"body": updated.body, "sources": updated.sources})
        revision = await add_revision(db, actor_id, page, document)
        revision.published_at = datetime.now(UTC)
        page.published_revision_uid = revision.uid
        page.version += 1
        result.updated += 1
    if result.updated:
        tree.version += 1
    await db.flush()
    return result
