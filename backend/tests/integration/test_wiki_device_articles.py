import asyncio
from uuid import uuid5

import pytest
from sqlalchemy import func, select
from test_wiki_admin import ROOT, doc
from test_wiki_read import wiki_setup

from vowen.core.errors import AppError
from vowen.modules.identity.models import User
from vowen.modules.references.fixtures import seed_references
from vowen.modules.references.models import Device
from vowen.modules.wiki.device_articles import seed_device_articles
from vowen.modules.wiki.models import WikiPage, WikiRevision, WikiSection
from vowen.modules.wiki.queries import published_page
from vowen.modules.wiki.seed import NAMESPACE, seed_reference_pages


async def setup(api, *, stubs=True):
    client, app, admin, member, section, _, existing, _, _ = await wiki_setup(api)
    async with app.state.sessions.begin() as db:
        await seed_references(db)
        actor = await db.scalar(select(WikiRevision.author_id).where(
            WikiRevision.page_uid == existing,
        ).limit(1))
        if stubs:
            await seed_reference_pages(db, actor)
    return client, app, admin, member, actor, section


async def test_upgrade_keeps_identity_images_history_and_repeated_import(api):
    _, app, _, _, actor, _ = await setup(api)
    async with app.state.sessions.begin() as db:
        devices = list(await db.scalars(select(Device)))
        before = {}
        for device in devices:
            uid = uuid5(NAMESPACE, "devices:" + str(device.uid))
            page = await published_page(db, uid)
            before[uid] = (page.revision_uid, page.document.thumbnail, page.document.body)
        result = await seed_device_articles(db, actor)
        assert (result.created, result.updated, result.skipped) == (0, 62, 0)
    async with app.state.sessions.begin() as db:
        for uid, (revision_uid, thumbnail, body) in before.items():
            current = await published_page(db, uid)
            assert len(current.document.body.split()) >= 100
            assert current.document.thumbnail == thumbnail
            assert current.revision_uid != revision_uid
            assert (await db.get(WikiRevision, revision_uid)).body == body
            assert (await db.get(WikiPage, uid)).version == 2
        count = await db.scalar(select(func.count()).select_from(WikiRevision))
        result = await seed_device_articles(db, actor)
        assert (result.created, result.updated, result.skipped) == (0, 0, 62)
        assert await db.scalar(select(func.count()).select_from(WikiRevision)) == count


async def test_manual_drafts_archives_and_moved_or_altered_stubs_are_preserved(api):
    client, app, admin, _, actor, section = await setup(api)
    async with app.state.sessions() as db:
        devices = list(await db.scalars(select(Device).order_by(Device.uid).limit(4)))
        ids = [uuid5(NAMESPACE, "devices:" + str(device.uid)) for device in devices]
    current = (await client.get(ROOT + f"/pages/{ids[0]}", headers=admin)).json()
    assert (await client.patch(ROOT + f"/pages/{ids[0]}", headers=admin, json={
        "expected_version": current["version"], "document": doc(section, "Ручная редакция"),
    })).status_code == 200
    assert (await client.post(ROOT + f"/pages/{ids[1]}/archive", headers=admin, json={
        "expected_version": 1, "archived": True,
    })).status_code == 200
    async with app.state.sessions.begin() as db:
        # Defensive checks also preserve directly altered historical/import records.
        page = await db.get(WikiPage, ids[2])
        (await db.get(WikiRevision, page.draft_revision_uid)).summary = "Сохранить аннотацию"
        page = await db.get(WikiPage, ids[3])
        (await db.get(WikiRevision, page.draft_revision_uid)).section_uid = section
        result = await seed_device_articles(db, actor)
        assert (result.created, result.updated, result.skipped) == (0, 58, 4)
    current = (await client.get(ROOT + f"/pages/{ids[0]}", headers=admin)).json()
    assert current["document"]["title"] == "Ручная редакция"
    async with app.state.sessions() as db:
        assert (await db.get(WikiPage, ids[1])).archived_at is not None


async def test_new_install_concurrent_import_and_member_denial(api):
    _, app, _, _, actor, _ = await setup(api, stubs=False)
    async with app.state.sessions() as db:
        member = await db.scalar(select(User.id).where(User.is_admin.is_(False)))
    with pytest.raises(AppError) as denied:
        async with app.state.sessions.begin() as db:
            await seed_device_articles(db, member)
    assert denied.value.status == 403

    async def run():
        async with app.state.sessions.begin() as db:
            return await seed_device_articles(db, actor)

    results = await asyncio.gather(run(), run())
    assert sorted(result.created for result in results) == [0, 62]
    assert sorted(result.skipped for result in results) == [0, 62]
    assert all(result.updated == 0 for result in results)


async def test_missing_device_rolls_back_without_partial_pages(api):
    _, app, _, _, actor, _ = await setup(api, stubs=False)
    from vowen.modules.references.models import PracticeDevice

    async with app.state.sessions.begin() as db:
        device = await db.scalar(select(Device).where(Device.extra["code"].astext == "hand"))
        # Remove a reference in this disposable test only; import must not make partial pages.
        from sqlalchemy import delete
        await db.execute(delete(PracticeDevice).where(PracticeDevice.device_uid == device.uid))
        await db.delete(device)
    with pytest.raises(AppError) as missing:
        async with app.state.sessions.begin() as db:
            await seed_device_articles(db, actor)
    assert missing.value.status == 422
    async with app.state.sessions() as db:
        assert await db.scalar(select(func.count()).select_from(WikiPage)) == 3
        assert await db.get(WikiSection, uuid5(NAMESPACE, "devices")) is None


async def test_concurrent_manual_save_is_preserved_or_reports_version_conflict(api):
    client, app, admin, _, actor, section = await setup(api)
    async with app.state.sessions() as db:
        device = await db.scalar(select(Device).where(Device.extra["code"].astext == "cuffs"))
        uid = uuid5(NAMESPACE, "devices:" + str(device.uid))

    async def import_articles():
        async with app.state.sessions.begin() as db:
            return await seed_device_articles(db, actor)

    imported, response = await asyncio.gather(
        import_articles(),
        client.patch(ROOT + f"/pages/{uid}", headers=admin, json={
            "expected_version": 1, "document": doc(section, "Одновременная ручная правка"),
        }),
    )
    current = (await client.get(ROOT + f"/pages/{uid}", headers=admin)).json()
    if response.status_code == 200:
        assert imported.updated == 61
        assert current["document"]["title"] == "Одновременная ручная правка"
    else:
        assert response.status_code == 409
        assert imported.updated == 62
        assert len(current["document"]["body"].split()) >= 100
