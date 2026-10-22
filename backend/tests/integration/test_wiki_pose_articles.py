import asyncio
from uuid import uuid4, uuid5

import pytest
from sqlalchemy import func, select
from test_wiki_admin import ROOT, doc
from test_wiki_device_articles import setup

from vowen.core.errors import AppError
from vowen.modules.identity.models import User
from vowen.modules.references.models import Pose, PoseComposition, PoseDevice
from vowen.modules.wiki.models import WikiPage, WikiRevision, WikiSection
from vowen.modules.wiki.pose_articles import load_pose_articles, seed_pose_articles
from vowen.modules.wiki.queries import published_page
from vowen.modules.wiki.seed import NAMESPACE


async def test_pose_upgrade_preserves_uids_images_categories_and_history(api):
    _, app, _, _, actor, _ = await setup(api)
    async with app.state.sessions.begin() as db:
        poses = {p.extra["code"]: p for p in await db.scalars(select(Pose))}
        compositions = list((await db.execute(select(
            PoseComposition.pose_uid, PoseComposition.composition_uid,
        ).order_by(PoseComposition.pose_uid, PoseComposition.composition_uid))).all())
        before = {}
        for article in load_pose_articles():
            reference = poses[article.code]
            uid = uuid5(NAMESPACE, "poses:" + str(reference.uid))
            old = await published_page(db, uid)
            before[uid] = old
        result = await seed_pose_articles(db, actor)
        assert (result.created, result.updated, result.skipped) == (0, 106, 0)
    async with app.state.sessions.begin() as db:
        after_compositions = list((await db.execute(select(
            PoseComposition.pose_uid, PoseComposition.composition_uid,
        ).order_by(PoseComposition.pose_uid, PoseComposition.composition_uid))).all())
        assert after_compositions == compositions
        for uid, old in before.items():
            page = await published_page(db, uid)
            assert len(page.document.body.split()) >= 80
            assert page.document.thumbnail == old.document.thumbnail
            assert page.document.section_uid == old.document.section_uid
            assert (await db.get(WikiRevision, old.revision_uid)).body == old.document.body
            assert (await db.get(WikiPage, uid)).version == 2
            expected = set(await db.scalars(select(PoseDevice.device_uid).where(
                PoseDevice.pose_uid == page.pose_uid,
            )))
            assert set(page.document.device_uids) == expected
        count = await db.scalar(select(func.count()).select_from(WikiRevision))
        result = await seed_pose_articles(db, actor)
        assert (result.created, result.updated, result.skipped) == (0, 0, 106)
        assert await db.scalar(select(func.count()).select_from(WikiRevision)) == count


async def test_pose_manual_draft_archive_and_moved_stub_are_untouched(api):
    client, app, admin, _, actor, section = await setup(api)
    async with app.state.sessions() as db:
        references = list(await db.scalars(select(Pose).where(
            Pose.extra["code"].astext.in_(["missionary", "spooning", "equipment-frame-standing"]),
        ).order_by(Pose.uid)))
        ids = [uuid5(NAMESPACE, "poses:" + str(p.uid)) for p in references]
    current = (await client.get(ROOT + f"/pages/{ids[0]}", headers=admin)).json()
    assert (await client.patch(ROOT + f"/pages/{ids[0]}", headers=admin, json={
        "expected_version": current["version"], "document": doc(section, "Мой текст позы"),
    })).status_code == 200
    assert (await client.post(ROOT + f"/pages/{ids[1]}/archive", headers=admin, json={
        "expected_version": 1, "archived": True,
    })).status_code == 200
    async with app.state.sessions.begin() as db:
        page = await db.get(WikiPage, ids[2])
        (await db.get(WikiRevision, page.draft_revision_uid)).section_uid = section
        result = await seed_pose_articles(db, actor)
        assert (result.created, result.updated, result.skipped) == (0, 103, 3)
    current = (await client.get(ROOT + f"/pages/{ids[0]}", headers=admin)).json()
    assert current["document"]["title"] == "Мой текст позы"


async def test_new_pose_import_is_concurrent_idempotent_and_admin_only(api):
    _, app, _, _, actor, _ = await setup(api, stubs=False)
    async with app.state.sessions() as db:
        member = await db.scalar(select(User.id).where(User.is_admin.is_(False)))
    with pytest.raises(AppError) as denied:
        async with app.state.sessions.begin() as db:
            await seed_pose_articles(db, member)
    assert denied.value.status == 403

    async def run():
        async with app.state.sessions.begin() as db:
            return await seed_pose_articles(db, actor)

    results = await asyncio.gather(run(), run())
    assert sorted(r.created for r in results) == [0, 106]
    assert sorted(r.skipped for r in results) == [0, 106]


@pytest.mark.parametrize("ambiguous", [False, True])
async def test_invalid_pose_code_does_not_publish_partial_content(api, ambiguous):
    _, app, _, _, actor, _ = await setup(api, stubs=False)
    async with app.state.sessions.begin() as db:
        pose = await db.scalar(select(Pose).where(
            Pose.extra["code"].astext == "missionary",
        ))
        if ambiguous:
            db.add(Pose(
                name="Another", description="", category_uid=pose.category_uid,
                extra={"code": "missionary"},
            ))
        else:
            pose.extra = {"code": "custom-code"}
    with pytest.raises(AppError) as invalid:
        async with app.state.sessions.begin() as db:
            await seed_pose_articles(db, actor)
    assert invalid.value.status == 422
    async with app.state.sessions() as db:
        assert await db.scalar(select(func.count()).select_from(WikiPage)) == 3
        assert await db.get(WikiSection, uuid5(NAMESPACE, "poses")) is None


async def test_pose_import_cannot_create_sections_below_depth_limit(api):
    _, app, _, _, actor, parent = await setup(api, stubs=False)
    async with app.state.sessions.begin() as db:
        for depth in range(2, 8):
            section = WikiSection(uid=uuid4(), parent_uid=parent, title=f"Depth {depth}")
            db.add(section)
            await db.flush()
            parent = section.uid
        db.add(WikiSection(
            uid=uuid5(NAMESPACE, "poses"), parent_uid=parent, title="Практики",
        ))
    with pytest.raises(AppError) as invalid:
        async with app.state.sessions.begin() as db:
            await seed_pose_articles(db, actor)
    assert invalid.value.status == 422
    async with app.state.sessions() as db:
        assert await db.scalar(select(func.count()).select_from(WikiPage)) == 3
        assert await db.scalar(select(func.count()).select_from(WikiSection)) == 9
