import asyncio
import hashlib

import pytest
from sqlalchemy import func, select
from test_wiki_admin import ROOT, doc
from test_wiki_read import wiki_setup

from vowen.core.errors import AppError
from vowen.modules.identity.models import User
from vowen.modules.references.fixtures import seed_references
from vowen.modules.wiki import editorial
from vowen.modules.wiki.editorial import editorial_uid
from vowen.modules.wiki.editorial_refresh import load_editorial_baselines, refresh_editorial_pages
from vowen.modules.wiki.models import WikiPage, WikiRevision
from vowen.modules.wiki.queries import published_page


async def setup(api, monkeypatch):
    client, app, admin, member, section, _, existing, _, _ = await wiki_setup(api)
    corpus = editorial.load_editorial()
    baselines = load_editorial_baselines()
    old_keys = {b.article.key for b in baselines}
    previous = corpus.model_copy(update={"articles": [b.article for b in baselines] + [
        a for a in corpus.articles if a.key not in old_keys
    ]})
    # Use deterministic old bodies and matching hashes to exercise upgrade eligibility.
    # Real production baselines contain hashes, not duplicate copies of old full texts.
    for article in previous.articles[:len(baselines)]:
        article.body = "Прежняя редакционная статья: " + article.key
        baseline = next(b for b in baselines if b.article.key == article.key)
        baseline.body_sha256 = hashlib.sha256(article.body.encode()).hexdigest()
    monkeypatch.setattr(editorial, "load_editorial", lambda: previous)
    async with app.state.sessions.begin() as db:
        await seed_references(db)
        actor = await db.scalar(select(WikiRevision.author_id).where(
            WikiRevision.page_uid == existing,
        ).limit(1))
        await editorial.seed_editorial_pages(db, actor)
    monkeypatch.setattr(editorial, "load_editorial", lambda: corpus)
    from vowen.modules.wiki import editorial_refresh
    monkeypatch.setattr(editorial_refresh, "load_editorial_baselines", lambda: baselines)
    return client, app, admin, member, section, actor, corpus


async def test_refresh_publishes_sources_preserves_history_and_is_idempotent(api, monkeypatch):
    _, app, _, _, _, actor, corpus = await setup(api, monkeypatch)
    async with app.state.sessions() as db:
        before = {
            a.key: await published_page(db, editorial_uid("article:" + a.key))
            for a in corpus.articles
        }
    async with app.state.sessions.begin() as db:
        result = await refresh_editorial_pages(db, actor)
        assert (result.created, result.updated, result.skipped) == (0, 33, 16)
    async with app.state.sessions.begin() as db:
        for article in corpus.articles:
            page = await published_page(db, editorial_uid("article:" + article.key))
            assert page.document.body == article.body
            assert page.document.sources == article.sources
            old = before[article.key]
            assert (await db.get(WikiRevision, old.revision_uid)).body == old.document.body
        count = await db.scalar(select(func.count()).select_from(WikiRevision))
        again = await refresh_editorial_pages(db, actor)
        assert (again.created, again.updated, again.skipped) == (0, 0, 49)
        assert await db.scalar(select(func.count()).select_from(WikiRevision)) == count


async def test_refresh_preserves_drafts_archive_move_and_modified_sources(api, monkeypatch):
    client, app, admin, _, section, actor, _ = await setup(api, monkeypatch)
    ids = [editorial_uid("article:" + k) for k in
           ("bdsm", "roles", "negotiation", "boundaries")]
    current = (await client.get(ROOT + f"/pages/{ids[0]}", headers=admin)).json()
    assert (await client.patch(ROOT + f"/pages/{ids[0]}", headers=admin, json={
        "expected_version": current["version"], "document": doc(section, "Моя статья"),
    })).status_code == 200
    archive = (await client.get(ROOT + f"/pages/{ids[1]}", headers=admin)).json()
    assert (await client.post(ROOT + f"/pages/{ids[1]}/archive", headers=admin, json={
        "expected_version": archive["version"], "archived": True,
    })).status_code == 200
    async with app.state.sessions.begin() as db:
        moved = await db.get(WikiPage, ids[2])
        (await db.get(WikiRevision, moved.published_revision_uid)).section_uid = section
        changed = await db.get(WikiPage, ids[3])
        (await db.get(WikiRevision, changed.published_revision_uid)).sources = [
            {"name": "Мой источник", "url": "https://example.org/source"},
        ]
        result = await refresh_editorial_pages(db, actor)
        assert (result.created, result.updated, result.skipped) == (0, 29, 20)
        assert (await db.get(WikiRevision, moved.published_revision_uid)).section_uid == section
        assert (await db.get(WikiRevision, changed.published_revision_uid)).sources[0]["name"] == (
            "Мой источник"
        )
    edit = (await client.get(ROOT + f"/pages/{ids[0]}", headers=admin)).json()
    assert edit["document"]["title"] == "Моя статья"


async def test_refresh_is_admin_only_and_concurrent(api, monkeypatch):
    _, app, _, _, _, actor, _ = await setup(api, monkeypatch)
    async with app.state.sessions() as db:
        member = await db.scalar(select(User.id).where(User.is_admin.is_(False)))
    with pytest.raises(AppError) as denied:
        async with app.state.sessions.begin() as db:
            await refresh_editorial_pages(db, member)
    assert denied.value.status == 403

    async def run():
        async with app.state.sessions.begin() as db:
            return await refresh_editorial_pages(db, actor)

    results = await asyncio.gather(run(), run())
    assert sorted(r.updated for r in results) == [0, 33]
    assert all(r.created == 0 for r in results)


async def test_refresh_on_fresh_install_creates_current_articles_once(api):
    _, app, _, _, _, _, existing, _, _ = await wiki_setup(api)
    async with app.state.sessions.begin() as db:
        await seed_references(db)
        actor = await db.scalar(select(WikiRevision.author_id).where(
            WikiRevision.page_uid == existing,
        ).limit(1))
        result = await refresh_editorial_pages(db, actor)
        assert (result.created, result.updated, result.skipped) == (49, 0, 0)
        again = await refresh_editorial_pages(db, actor)
        assert (again.created, again.updated, again.skipped) == (0, 0, 49)


async def test_refresh_rolls_back_missing_reference_on_existing_article(api, monkeypatch):
    _, app, _, _, _, actor, corpus = await setup(api, monkeypatch)
    changed = corpus.model_copy(deep=True)
    target = next(a for a in changed.articles if a.key == "equipment-collection")
    target.device_codes.append("does-not-exist")
    monkeypatch.setattr(editorial, "load_editorial", lambda: changed)
    async with app.state.sessions() as db:
        before = await db.scalar(select(func.count()).select_from(WikiRevision))
    with pytest.raises(AppError) as missing:
        async with app.state.sessions.begin() as db:
            await refresh_editorial_pages(db, actor)
    assert missing.value.status == 422
    async with app.state.sessions() as db:
        assert await db.scalar(select(func.count()).select_from(WikiRevision)) == before


async def test_refresh_race_with_manual_save_keeps_edit_or_returns_conflict(api, monkeypatch):
    client, app, admin, _, section, actor, _ = await setup(api, monkeypatch)
    uid = editorial_uid("article:privacy")

    async def refresh():
        async with app.state.sessions.begin() as db:
            return await refresh_editorial_pages(db, actor)

    result, response = await asyncio.gather(
        refresh(),
        client.patch(ROOT + f"/pages/{uid}", headers=admin, json={
            "expected_version": 1, "document": doc(section, "Моя одновременная правка"),
        }),
    )
    current = (await client.get(ROOT + f"/pages/{uid}", headers=admin)).json()
    if response.status_code == 200:
        assert result.updated == 32
        assert current["document"]["title"] == "Моя одновременная правка"
    else:
        assert response.status_code == 409
        assert result.updated == 33
        assert "## Источники и пояснения" in current["document"]["body"]
