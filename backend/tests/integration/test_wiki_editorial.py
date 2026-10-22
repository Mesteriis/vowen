import asyncio

import pytest
from sqlalchemy import func, select
from test_wiki_admin import ROOT, doc
from test_wiki_read import wiki_setup

from vowen.core.errors import AppError
from vowen.modules.references.fixtures import seed_references
from vowen.modules.wiki.editorial import editorial_uid, seed_editorial_pages
from vowen.modules.wiki.models import WikiPage, WikiRevision
from vowen.modules.wiki.queries import published_page


async def test_editorial_import_publishes_links_and_preserves_edits_archives(api):
    client, app, admin, _, section, _, existing, _, _ = await wiki_setup(api)
    async with app.state.sessions.begin() as db:
        await seed_references(db)
        author = (await db.get(WikiRevision, (await db.get(WikiPage, existing)).draft_revision_uid))
        actor_id = author.author_id
        result = await seed_editorial_pages(db, actor_id)
        assert result.created == 49 and result.skipped == 0
    uid = editorial_uid("article:bondage")
    async with app.state.sessions() as db:
        page = await published_page(db, uid)
        assert page.document.title == "Бондаж: формы и назначение"
        assert len(page.document.body.split()) >= 170
        assert len(page.document.practice_uids) == 2
        assert len(page.document.device_uids) == 5
        current = await db.get(WikiPage, uid)
        assert current.draft_revision_uid == current.published_revision_uid
    first = (await client.get(ROOT + f"/pages/{uid}", headers=admin)).json()
    assert (await client.patch(ROOT + f"/pages/{uid}", headers=admin, json={
        "expected_version": first["version"], "document": doc(section, "Редакторская правка"),
    })).status_code == 200
    archive_uid = editorial_uid("article:roles")
    archive = (await client.get(ROOT + f"/pages/{archive_uid}", headers=admin)).json()
    assert (await client.post(ROOT + f"/pages/{archive_uid}/archive", headers=admin, json={
        "expected_version": archive["version"], "archived": True,
    })).status_code == 200
    async with app.state.sessions.begin() as db:
        before = await db.scalar(select(func.count()).select_from(WikiRevision))
        result = await seed_editorial_pages(db, actor_id)
        assert (result.created, result.skipped) == (0, 49)
        assert await db.scalar(select(func.count()).select_from(WikiRevision)) == before
        assert (await db.get(WikiPage, archive_uid)).archived_at is not None
    edit = (await client.get(ROOT + f"/pages/{uid}", headers=admin)).json()
    assert edit["document"]["title"] == "Редакторская правка"


async def test_editorial_import_requires_admin_and_is_atomic_when_links_are_missing(api):
    _, app, _, _, _, _, existing, _, _ = await wiki_setup(api)
    from vowen.modules.identity.models import User

    async with app.state.sessions() as db:
        member = await db.scalar(select(User.id).where(User.is_admin.is_(False)))
        author = await db.scalar(select(WikiRevision.author_id).where(
            WikiRevision.page_uid == existing,
        ).limit(1))
    with pytest.raises(AppError) as denied:
        async with app.state.sessions.begin() as db:
            await seed_editorial_pages(db, member)
    assert denied.value.status == 403
    with pytest.raises(AppError) as missing:
        async with app.state.sessions.begin() as db:
            await seed_editorial_pages(db, author)
    assert missing.value.status == 422
    async with app.state.sessions() as db:
        assert await db.scalar(select(func.count()).select_from(WikiPage)) == 3


async def test_concurrent_editorial_import_has_no_duplicates(api):
    _, app, _, _, _, _, existing, _, _ = await wiki_setup(api)
    async with app.state.sessions.begin() as db:
        await seed_references(db)
        actor = await db.scalar(select(WikiRevision.author_id).where(
            WikiRevision.page_uid == existing,
        ).limit(1))

    async def run():
        async with app.state.sessions.begin() as db:
            return await seed_editorial_pages(db, actor)

    results = await asyncio.gather(run(), run())
    assert sorted(result.created for result in results) == [0, 49]


async def test_editorial_extension_adds_only_new_articles(api, monkeypatch):
    from vowen.modules.wiki import editorial

    _, app, _, _, _, _, existing, _, _ = await wiki_setup(api)
    corpus = editorial.load_editorial()
    initial = corpus.model_copy(update={"articles": corpus.articles[:25]})
    monkeypatch.setattr(editorial, "load_editorial", lambda: initial)
    async with app.state.sessions.begin() as db:
        await seed_references(db)
        actor = await db.scalar(select(WikiRevision.author_id).where(
            WikiRevision.page_uid == existing,
        ).limit(1))
        first = await seed_editorial_pages(db, actor)
        assert (first.created, first.skipped) == (25, 0)
        preserved = {
            a.key: (await published_page(db, editorial_uid("article:" + a.key))).revision_uid
            for a in initial.articles
        }
        before = await db.scalar(select(func.count()).select_from(WikiRevision))
    monkeypatch.setattr(editorial, "load_editorial", lambda: corpus)
    async with app.state.sessions.begin() as db:
        result = await seed_editorial_pages(db, actor)
        assert (result.created, result.skipped) == (24, 25)
        assert await db.scalar(select(func.count()).select_from(WikiRevision)) == before + 24
        for key, revision in preserved.items():
            page = await published_page(db, editorial_uid("article:" + key))
            assert page.revision_uid == revision
        for article in corpus.articles[25:]:
            page = await published_page(db, editorial_uid("article:" + article.key))
            assert page.document.body == article.body
            assert page.document.summary == article.summary
        again = await seed_editorial_pages(db, actor)
        assert (again.created, again.skipped) == (0, 49)
        assert await db.scalar(select(func.count()).select_from(WikiRevision)) == before + 24
