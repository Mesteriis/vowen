import asyncio
from datetime import UTC, datetime
from uuid import uuid5

import pytest
from sqlalchemy import func, select
from test_wiki_admin import ROOT, doc
from test_wiki_device_articles import setup as base_setup

from vowen.core.errors import AppError
from vowen.modules.identity.models import User
from vowen.modules.references.fixtures import fixture_rows
from vowen.modules.wiki.editorial import editorial_uid, seed_editorial_pages
from vowen.modules.wiki.models import WikiPage, WikiRevision
from vowen.modules.wiki.practice_articles import seed_practice_articles
from vowen.modules.wiki.practice_review import (
    load_practice_reviews,
    load_reviewed_practice_articles,
    refresh_practice_pages,
)
from vowen.modules.wiki.queries import published_page
from vowen.modules.wiki.seed import NAMESPACE


def practice_uid(code):
    row = next(r for r in fixture_rows("practices") if r["extra"]["code"] == code)
    return uuid5(NAMESPACE, "practices:" + str(row["uid"]))


async def setup(api, stubs=True):
    client, app, admin, member, actor, section = await base_setup(api, stubs=stubs)
    async with app.state.sessions.begin() as db:
        await seed_practice_articles(db, actor)
        await seed_editorial_pages(db, actor)
    return client, app, admin, member, actor, section


@pytest.mark.parametrize("stubs", [False, True])
async def test_review_retains_history_and_metadata_for_both_original_import_paths(api, stubs):
    _, app, _, _, actor, _ = await setup(api, stubs)
    reviews = {r.code: r for r in load_practice_reviews()}
    async with app.state.sessions() as db:
        before = {c: await published_page(db, practice_uid(c)) for c in reviews}
        versions = {c: (await db.get(WikiPage, practice_uid(c))).version for c in reviews}
    async with app.state.sessions.begin() as db:
        result = await refresh_practice_pages(db, actor)
        assert (result.updated, result.skipped) == (93, 0)
    enriched = {a.code: a for a in load_reviewed_practice_articles()}
    async with app.state.sessions.begin() as db:
        for code, old in before.items():
            current = await published_page(db, practice_uid(code))
            assert (await db.get(WikiPage, practice_uid(code))).version == versions[code] + 1
            assert current.document.body == enriched[code].body
            assert current.document.sources == enriched[code].sources
            assert current.document.model_dump(exclude={"body", "sources"}) == (
                old.document.model_dump(exclude={"body", "sources"})
            )
            assert (await db.get(WikiRevision, old.revision_uid)).body == old.document.body
        count = await db.scalar(select(func.count()).select_from(WikiRevision))
        again = await refresh_practice_pages(db, actor)
        assert (again.updated, again.skipped) == (0, 93)
        assert await db.scalar(select(func.count()).select_from(WikiRevision)) == count


async def test_review_preserves_drafts_moved_pages_and_modified_source_metadata(api):
    client, app, admin, _, actor, section = await setup(api)
    ids = [practice_uid(c) for c in ("roleplay", "latex", "service")]
    assert (await client.patch(ROOT + f"/pages/{ids[0]}", headers=admin, json={
        "expected_version": 2, "document": doc(section, "Мой черновик"),
    })).status_code == 200
    async with app.state.sessions.begin() as db:
        moved = await db.get(WikiPage, ids[1])
        (await db.get(WikiRevision, moved.published_revision_uid)).section_uid = section
        modified = await db.get(WikiPage, ids[2])
        (await db.get(WikiRevision, modified.published_revision_uid)).sources = [
            {"name": "Мой источник", "url": "https://example.org/personal"},
        ]
        result = await refresh_practice_pages(db, actor)
        assert (result.updated, result.skipped) == (90, 3)
        assert (await db.get(WikiRevision, moved.published_revision_uid)).section_uid == section
        assert (await db.get(WikiRevision, modified.published_revision_uid)).sources[0]["name"] == (
            "Мой источник"
        )
    assert (await client.get(ROOT + f"/pages/{ids[0]}", headers=admin)).json()[
        "document"
    ]["title"] == "Мой черновик"


async def test_review_rejects_archived_link_target_and_rolls_back(api):
    _, app, _, _, actor, _ = await setup(api)
    uid = editorial_uid("article:extended-dynamics")
    async with app.state.sessions.begin() as db:
        (await db.get(WikiPage, uid)).archived_at = datetime.now(UTC)
    async with app.state.sessions() as db:
        count = await db.scalar(select(func.count()).select_from(WikiRevision))
    with pytest.raises(AppError) as blocked:
        async with app.state.sessions.begin() as db:
            await refresh_practice_pages(db, actor)
    assert blocked.value.code == "INVALID_WIKI_LINK"
    async with app.state.sessions() as db:
        assert await db.scalar(select(func.count()).select_from(WikiRevision)) == count
        assert (await db.get(WikiPage, uid)).archived_at is not None


async def test_review_checks_administrator_and_serializes_concurrent_runs(api):
    _, app, _, _, actor, _ = await setup(api)
    async with app.state.sessions() as db:
        member = await db.scalar(select(User.id).where(User.is_admin.is_(False)))
    with pytest.raises(AppError) as denied:
        async with app.state.sessions.begin() as db:
            await refresh_practice_pages(db, member)
    assert denied.value.status == 403

    async def run():
        async with app.state.sessions.begin() as db:
            return await refresh_practice_pages(db, actor)

    results = await asyncio.gather(run(), run())
    assert sorted(r.updated for r in results) == [0, 93]


async def test_review_race_with_editor_does_not_replace_the_edit(api):
    client, app, admin, _, actor, section = await setup(api)
    uid = practice_uid("roleplay")

    async def review():
        async with app.state.sessions.begin() as db:
            return await refresh_practice_pages(db, actor)

    result, saved = await asyncio.gather(review(), client.patch(
        ROOT + f"/pages/{uid}", headers=admin, json={
            "expected_version": 2, "document": doc(section, "Моя одновременная правка"),
        },
    ))
    current = (await client.get(ROOT + f"/pages/{uid}", headers=admin)).json()
    if saved.status_code == 200:
        assert result.updated == 92
        assert current["document"]["title"] == "Моя одновременная правка"
    else:
        assert saved.status_code == 409 and result.updated == 93
        assert "## Источники и область подтверждения" in current["document"]["body"]


async def test_extended_review_keeps_already_reviewed_publications_unchanged(api, monkeypatch):
    from vowen.modules.wiki import practice_review

    _, app, _, _, actor, _ = await setup(api)
    reviews = load_practice_reviews()
    monkeypatch.setattr(practice_review, "load_practice_reviews", lambda: reviews[:27])
    async with app.state.sessions.begin() as db:
        first = await refresh_practice_pages(db, actor)
        assert (first.updated, first.skipped) == (27, 0)
    async with app.state.sessions() as db:
        published = {r.code: (await db.get(WikiPage, practice_uid(r.code))).published_revision_uid
                     for r in reviews[:27]}
    monkeypatch.setattr(practice_review, "load_practice_reviews", lambda: reviews)
    async with app.state.sessions.begin() as db:
        extended = await refresh_practice_pages(db, actor)
        assert (extended.updated, extended.skipped) == (66, 27)
        for code, uid in published.items():
            assert (await db.get(WikiPage, practice_uid(code))).published_revision_uid == uid
