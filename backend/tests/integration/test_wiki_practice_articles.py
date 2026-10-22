import asyncio
from uuid import uuid4, uuid5

import pytest
from sqlalchemy import func, select
from test_wiki_admin import ROOT, doc
from test_wiki_device_articles import setup

from vowen.core.errors import AppError
from vowen.modules.identity.models import User
from vowen.modules.references.models import Practice, PracticeDevice
from vowen.modules.wiki.models import WikiPage, WikiRevision, WikiSection
from vowen.modules.wiki.practice_articles import load_practice_articles, seed_practice_articles
from vowen.modules.wiki.queries import published_page
from vowen.modules.wiki.seed import NAMESPACE


async def test_practice_upgrade_preserves_uids_images_categories_and_history(api):
    _, app, _, _, actor, _ = await setup(api)
    async with app.state.sessions.begin() as db:
        practices = {p.extra["code"]: p for p in await db.scalars(select(Practice))}
        before = {}
        for article in load_practice_articles():
            reference = practices[article.code]
            uid = uuid5(NAMESPACE, "practices:" + str(reference.uid))
            old = await published_page(db, uid)
            before[uid] = old
        result = await seed_practice_articles(db, actor)
        assert (result.created, result.updated, result.skipped) == (0, 93, 0)
    async with app.state.sessions.begin() as db:
        for uid, old in before.items():
            page = await published_page(db, uid)
            assert len(page.document.body.split()) >= 110
            assert page.document.thumbnail == old.document.thumbnail
            assert page.document.section_uid == old.document.section_uid
            assert (await db.get(WikiRevision, old.revision_uid)).body == old.document.body
            assert (await db.get(WikiPage, uid)).version == 2
            expected = set(await db.scalars(select(PracticeDevice.device_uid).where(
                PracticeDevice.practice_uid == page.practice_uid,
            )))
            assert set(page.document.device_uids) == expected
        count = await db.scalar(select(func.count()).select_from(WikiRevision))
        result = await seed_practice_articles(db, actor)
        assert (result.created, result.updated, result.skipped) == (0, 0, 93)
        assert await db.scalar(select(func.count()).select_from(WikiRevision)) == count


async def test_practice_manual_draft_archive_and_moved_stub_are_untouched(api):
    client, app, admin, _, actor, section = await setup(api)
    async with app.state.sessions() as db:
        references = list(await db.scalars(select(Practice).where(
            Practice.extra["code"].astext.in_(["bondage", "protocol", "service"]),
        ).order_by(Practice.uid)))
        ids = [uuid5(NAMESPACE, "practices:" + str(p.uid)) for p in references]
    current = (await client.get(ROOT + f"/pages/{ids[0]}", headers=admin)).json()
    assert (await client.patch(ROOT + f"/pages/{ids[0]}", headers=admin, json={
        "expected_version": current["version"], "document": doc(section, "Мой текст практики"),
    })).status_code == 200
    assert (await client.post(ROOT + f"/pages/{ids[1]}/archive", headers=admin, json={
        "expected_version": 1, "archived": True,
    })).status_code == 200
    async with app.state.sessions.begin() as db:
        page = await db.get(WikiPage, ids[2])
        (await db.get(WikiRevision, page.draft_revision_uid)).section_uid = section
        result = await seed_practice_articles(db, actor)
        assert (result.created, result.updated, result.skipped) == (0, 90, 3)
    current = (await client.get(ROOT + f"/pages/{ids[0]}", headers=admin)).json()
    assert current["document"]["title"] == "Мой текст практики"


async def test_new_practice_import_is_concurrent_idempotent_and_admin_only(api):
    _, app, _, _, actor, _ = await setup(api, stubs=False)
    async with app.state.sessions() as db:
        member = await db.scalar(select(User.id).where(User.is_admin.is_(False)))
    with pytest.raises(AppError) as denied:
        async with app.state.sessions.begin() as db:
            await seed_practice_articles(db, member)
    assert denied.value.status == 403

    async def run():
        async with app.state.sessions.begin() as db:
            return await seed_practice_articles(db, actor)

    results = await asyncio.gather(run(), run())
    assert sorted(r.created for r in results) == [0, 93]
    assert sorted(r.skipped for r in results) == [0, 93]


@pytest.mark.parametrize("ambiguous", [False, True])
async def test_invalid_practice_code_does_not_publish_partial_content(api, ambiguous):
    _, app, _, _, actor, _ = await setup(api, stubs=False)
    async with app.state.sessions.begin() as db:
        practice = await db.scalar(select(Practice).where(
            Practice.extra["code"].astext == "bondage",
        ))
        if ambiguous:
            db.add(Practice(name="Another", description="", extra={"code": "bondage"}))
        else:
            practice.extra = {"code": "custom-code"}
    with pytest.raises(AppError) as invalid:
        async with app.state.sessions.begin() as db:
            await seed_practice_articles(db, actor)
    assert invalid.value.status == 422
    async with app.state.sessions() as db:
        assert await db.scalar(select(func.count()).select_from(WikiPage)) == 3
        assert await db.get(WikiSection, uuid5(NAMESPACE, "practices")) is None


async def test_practice_import_cannot_create_sections_below_depth_limit(api):
    _, app, _, _, actor, parent = await setup(api, stubs=False)
    async with app.state.sessions.begin() as db:
        for depth in range(2, 8):
            section = WikiSection(uid=uuid4(), parent_uid=parent, title=f"Depth {depth}")
            db.add(section)
            await db.flush()
            parent = section.uid
        db.add(WikiSection(
            uid=uuid5(NAMESPACE, "practices"), parent_uid=parent, title="Практики",
        ))
    with pytest.raises(AppError) as invalid:
        async with app.state.sessions.begin() as db:
            await seed_practice_articles(db, actor)
    assert invalid.value.status == 422
    async with app.state.sessions() as db:
        assert await db.scalar(select(func.count()).select_from(WikiPage)) == 3
        assert await db.scalar(select(func.count()).select_from(WikiSection)) == 9
