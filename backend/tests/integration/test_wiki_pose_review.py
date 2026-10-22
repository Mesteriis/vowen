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
from vowen.modules.wiki.catalogue_articles import seed_catalogue_articles
from vowen.modules.wiki.editorial import editorial_uid, seed_editorial_pages
from vowen.modules.wiki.models import WikiPage, WikiRevision
from vowen.modules.wiki.pose_articles import seed_pose_articles
from vowen.modules.wiki.pose_review import (
    load_pose_reviews,
    load_reviewed_pose_articles,
    refresh_pose_pages,
)
from vowen.modules.wiki.queries import published_page
from vowen.modules.wiki.seed import NAMESPACE, seed_reference_pages


def pose_uid(code):
    row = next(r for r in fixture_rows("poses") if r["extra"]["code"] == code)
    return uuid5(NAMESPACE, "poses:" + str(row["uid"]))


async def setup(api, stubs=True):
    client, app, admin, member, actor, section = await base_setup(api, stubs=stubs)
    async with app.state.sessions.begin() as db:
        await seed_pose_articles(db, actor)
        await seed_reference_pages(db, actor)
        await seed_editorial_pages(db, actor)
        await seed_catalogue_articles(db, actor)
    return client, app, admin, member, actor, section


@pytest.mark.parametrize("stubs", [False, True])
async def test_review_retains_history_and_metadata_for_both_original_import_paths(api, stubs):
    _, app, _, _, actor, _ = await setup(api, stubs)
    reviews = {r.code: r for r in load_pose_reviews()}
    async with app.state.sessions() as db:
        before = {c: await published_page(db, pose_uid(c)) for c in reviews}
        versions = {c: (await db.get(WikiPage, pose_uid(c))).version for c in reviews}
    async with app.state.sessions.begin() as db:
        result = await refresh_pose_pages(db, actor)
        assert (result.updated, result.skipped) == (106, 0)
    enriched = {a.code: a for a in load_reviewed_pose_articles()}
    async with app.state.sessions.begin() as db:
        for code, old in before.items():
            current = await published_page(db, pose_uid(code))
            assert (await db.get(WikiPage, pose_uid(code))).version == versions[code] + 1
            assert current.document.body == enriched[code].body
            assert current.document.sources == enriched[code].sources
            assert current.document.model_dump(exclude={"body", "sources"}) == (
                old.document.model_dump(exclude={"body", "sources"})
            )
            assert (await db.get(WikiRevision, old.revision_uid)).body == old.document.body
        count = await db.scalar(select(func.count()).select_from(WikiRevision))
        again = await refresh_pose_pages(db, actor)
        assert (again.updated, again.skipped) == (0, 106)
        assert await db.scalar(select(func.count()).select_from(WikiRevision)) == count


async def test_review_preserves_drafts_moved_pages_and_modified_source_metadata(api):
    client, app, admin, _, actor, section = await setup(api)
    ids = [pose_uid(c) for c in ("nadu", "tower", "inspection")]
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
        result = await refresh_pose_pages(db, actor)
        assert (result.updated, result.skipped) == (103, 3)
        assert (await db.get(WikiRevision, moved.published_revision_uid)).section_uid == section
        assert (await db.get(WikiRevision, modified.published_revision_uid)).sources[0]["name"] == (
            "Мой источник"
        )
    assert (await client.get(ROOT + f"/pages/{ids[0]}", headers=admin)).json()[
        "document"
    ]["title"] == "Мой черновик"


async def test_review_rejects_archived_link_target_and_rolls_back(api):
    _, app, _, _, actor, _ = await setup(api)
    uid = editorial_uid("article:positions")
    async with app.state.sessions.begin() as db:
        (await db.get(WikiPage, uid)).archived_at = datetime.now(UTC)
    async with app.state.sessions() as db:
        count = await db.scalar(select(func.count()).select_from(WikiRevision))
    with pytest.raises(AppError) as blocked:
        async with app.state.sessions.begin() as db:
            await refresh_pose_pages(db, actor)
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
            await refresh_pose_pages(db, member)
    assert denied.value.status == 403

    async def run():
        async with app.state.sessions.begin() as db:
            return await refresh_pose_pages(db, actor)

    results = await asyncio.gather(run(), run())
    assert sorted(r.updated for r in results) == [0, 106]


async def test_review_race_with_editor_does_not_replace_the_edit(api):
    client, app, admin, _, actor, section = await setup(api)
    uid = pose_uid("nadu")

    async def review():
        async with app.state.sessions.begin() as db:
            return await refresh_pose_pages(db, actor)

    result, saved = await asyncio.gather(review(), client.patch(
        ROOT + f"/pages/{uid}", headers=admin, json={
            "expected_version": 2, "document": doc(section, "Моя одновременная правка"),
        },
    ))
    current = (await client.get(ROOT + f"/pages/{uid}", headers=admin)).json()
    if saved.status_code == 200:
        assert result.updated == 105
        assert current["document"]["title"] == "Моя одновременная правка"
    else:
        assert saved.status_code == 409 and result.updated == 106
        assert "## Источники и область подтверждения" in current["document"]["body"]


async def test_wrong_catalogue_reference_rolls_back_the_entire_pose_review(api, monkeypatch):
    from vowen.modules.wiki import pose_review
    from vowen.modules.wiki.catalogue_articles import ReferencePointer

    _, app, _, _, actor, _ = await setup(api)
    reviews = load_pose_reviews()
    # A real category UID in the devices table must fail, not resolve by UUID alone.
    wrong = reviews[-1].model_copy(update={"related_references": [ReferencePointer(
        kind="devices", uid=reviews[-1].related_references[0].uid,
    )]})
    monkeypatch.setattr(pose_review, "load_pose_reviews", lambda: [*reviews[:-1], wrong])
    async with app.state.sessions() as db:
        count = await db.scalar(select(func.count()).select_from(WikiRevision))
    with pytest.raises(AppError) as rejected:
        async with app.state.sessions.begin() as db:
            await refresh_pose_pages(db, actor)
    assert rejected.value.code == "INVALID_EDITORIAL_REFERENCE"
    async with app.state.sessions() as db:
        assert await db.scalar(select(func.count()).select_from(WikiRevision)) == count


async def test_pose_review_preserves_changed_reference_list_and_thumbnail(api):
    from vowen.modules.references.models import Device
    from vowen.modules.wiki.models import WikiRevisionDevice

    _, app, _, _, actor, _ = await setup(api)
    uid = pose_uid("missionary")
    async with app.state.sessions.begin() as db:
        page = await db.get(WikiPage, uid)
        revision = await db.get(WikiRevision, page.published_revision_uid)
        linked = set(await db.scalars(select(WikiRevisionDevice.device_uid).where(
            WikiRevisionDevice.revision_uid == revision.uid,
        )))
        device = next(d for d in await db.scalars(select(Device.uid)) if d not in linked)
        db.add(WikiRevisionDevice(revision_uid=revision.uid, device_uid=device))
        other = await db.get(WikiPage, pose_uid("nadu"))
        thumbnail = fixture_rows("devices")[0]["thumbnail"]
        (await db.get(WikiRevision, other.published_revision_uid)).thumbnail = thumbnail
        result = await refresh_pose_pages(db, actor)
        assert (result.updated, result.skipped) == (104, 2)
        assert page.published_revision_uid == revision.uid
        assert (await db.get(WikiRevision, other.published_revision_uid)).thumbnail == thumbnail
