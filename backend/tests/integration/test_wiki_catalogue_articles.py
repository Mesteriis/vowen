import asyncio
from datetime import UTC, datetime

import pytest
from sqlalchemy import func, select
from test_wiki_admin import ROOT, doc
from test_wiki_read import wiki_setup

from vowen.core.errors import AppError
from vowen.modules.identity.models import User
from vowen.modules.references.fixtures import seed_references
from vowen.modules.wiki.catalogue_articles import (
    catalogue_page_uid,
    load_catalogue_articles,
    seed_catalogue_articles,
)
from vowen.modules.wiki.editorial import editorial_uid, seed_editorial_pages
from vowen.modules.wiki.models import WikiPage, WikiRevision
from vowen.modules.wiki.queries import published_page
from vowen.modules.wiki.seed import seed_reference_pages


async def setup(api):
    client, app, admin, _, section, _, existing, _, _ = await wiki_setup(api)
    async with app.state.sessions.begin() as db:
        await seed_references(db)
        actor = await db.scalar(select(WikiRevision.author_id).where(
            WikiRevision.page_uid == existing,
        ).limit(1))
        await seed_editorial_pages(db, actor)
        await seed_reference_pages(db, actor)
    return client, app, admin, section, actor


async def test_catalogue_import_links_pages_and_preserves_user_changes(api):
    client, app, admin, section, actor = await setup(api)
    async with app.state.sessions.begin() as db:
        result = await seed_catalogue_articles(db, actor)
        assert (result.created, result.skipped) == (177, 0)
    articles = load_catalogue_articles()
    async with app.state.sessions() as db:
        for article in articles:
            uid = catalogue_page_uid(article.reference.kind, article.reference.uid)
            page = await published_page(db, uid)
            assert article.body.strip() in page.document.body
            assert page.document.sources == article.sources
            for pointer in article.related_references:
                target = catalogue_page_uid(pointer.kind, pointer.uid)
                assert f"#wiki?page={target}" in page.document.body
                assert await published_page(db, target)
            for target in article.related_pages:
                assert f"#wiki?page={target}" in page.document.body
                assert await published_page(db, target)
    edited = catalogue_page_uid(articles[0].reference.kind, articles[0].reference.uid)
    archived = catalogue_page_uid(articles[1].reference.kind, articles[1].reference.uid)
    assert (await client.patch(ROOT + f"/pages/{edited}", headers=admin, json={
        "expected_version": 1, "document": doc(section, "Моя карточка"),
    })).status_code == 200
    assert (await client.post(ROOT + f"/pages/{archived}/archive", headers=admin, json={
        "expected_version": 1, "archived": True,
    })).status_code == 200
    async with app.state.sessions.begin() as db:
        count = await db.scalar(select(func.count()).select_from(WikiRevision))
        repeat = await seed_catalogue_articles(db, actor)
        assert (repeat.created, repeat.skipped) == (0, 177)
        assert await db.scalar(select(func.count()).select_from(WikiRevision)) == count
        assert (await db.get(WikiPage, archived)).archived_at is not None
    assert (await client.get(ROOT + f"/pages/{edited}", headers=admin)).json()[
        "document"
    ]["title"] == "Моя карточка"


async def test_catalogue_import_is_admin_only_and_concurrent(api):
    _, app, _, _, actor = await setup(api)
    async with app.state.sessions() as db:
        member = await db.scalar(select(User.id).where(User.is_admin.is_(False)))
    with pytest.raises(AppError) as denied:
        async with app.state.sessions.begin() as db:
            await seed_catalogue_articles(db, member)
    assert denied.value.status == 403

    async def run():
        async with app.state.sessions.begin() as db:
            return await seed_catalogue_articles(db, actor)

    results = await asyncio.gather(run(), run())
    assert sorted(r.created for r in results) == [0, 177]
    assert sorted(r.skipped for r in results) == [0, 177]


async def test_catalogue_import_rejects_unpublished_link_and_rolls_back(api):
    _, app, _, _, actor = await setup(api)
    async with app.state.sessions.begin() as db:
        (await db.get(WikiPage, editorial_uid("article:privacy"))).archived_at = (
            datetime.now(UTC)
        )
    async with app.state.sessions() as db:
        count = await db.scalar(select(func.count()).select_from(WikiPage))
    with pytest.raises(AppError) as missing:
        async with app.state.sessions.begin() as db:
            await seed_catalogue_articles(db, actor)
    assert missing.value.code == "INVALID_WIKI_LINK"
    async with app.state.sessions() as db:
        assert await db.scalar(select(func.count()).select_from(WikiPage)) == count
