import asyncio

from test_wiki_admin import ROOT, doc
from test_wiki_read import wiki_setup

from vowen.modules.references.fixtures import seed_references


async def test_seed_is_idempotent_and_preserves_edits_and_archives(api):
    client, app, admin, member, a, _, _, _, _ = await wiki_setup(api)
    async with app.state.sessions.begin() as db:
        await seed_references(db)
    url = ROOT + "/seed-references"
    assert (await client.post(url, headers=member)).status_code == 403
    result = await client.post(url, headers=admin)
    assert result.status_code == 200, result.text
    assert result.json() == {"created": 261, "skipped": 0}
    tree = (await client.get("/api/v1/wiki/tree", headers=member)).json()
    assert len(tree["pages"]) == 262
    ids = [p["uid"] for p in tree["pages"] if p["kind"] == "encyclopedia"]
    first = (await client.get(ROOT + f"/pages/{ids[0]}", headers=admin)).json()
    r = await client.patch(
        ROOT + f"/pages/{ids[0]}",
        headers=admin,
        json={"expected_version": first["version"], "document": doc(a, "Local edit")},
    )
    assert r.status_code == 200
    second = (await client.get(ROOT + f"/pages/{ids[1]}", headers=admin)).json()
    assert (
        await client.post(
            ROOT + f"/pages/{ids[1]}/archive",
            headers=admin,
            json={"expected_version": second["version"], "archived": True},
        )
    ).status_code == 200
    r = await client.post(url, headers=admin)
    assert r.json() == {"created": 0, "skipped": 261}
    assert (await client.get(ROOT + f"/pages/{ids[0]}", headers=admin)).json()["document"][
        "title"
    ] == "Local edit"
    assert (await client.get("/api/v1/wiki/pages/" + ids[1], headers=member)).status_code == 404
    from vowen.modules.references.models import Device

    async with app.state.sessions.begin() as db:
        db.add(Device(name="Custom device", description="Custom description"))
    r = await client.post(url, headers=admin)
    assert r.json() == {"created": 1, "skipped": 261}


async def test_concurrent_import_has_no_duplicates(api):
    client, app, admin, _, _, _, _, _, _ = await wiki_setup(api)
    async with app.state.sessions.begin() as db:
        await seed_references(db)
    results = await asyncio.gather(
        *[client.post(ROOT + "/seed-references", headers=admin) for _ in range(2)]
    )
    assert all(r.status_code == 200 for r in results)
    assert sorted(r.json()["created"] for r in results) == [0, 261]


async def test_failed_import_rolls_back_all_created_pages(api, monkeypatch):
    import pytest
    from sqlalchemy import func, select

    from vowen.modules.wiki import seed
    from vowen.modules.wiki.models import WikiPage

    client, app, admin, _, _, _, _, _, _ = await wiki_setup(api)
    async with app.state.sessions.begin() as db:
        await seed_references(db)
        before = await db.scalar(select(func.count()).select_from(WikiPage))
    original = seed.add_revision

    async def injected_failure(*args, **kwargs):
        await original(*args, **kwargs)
        raise RuntimeError("Injected import failure")

    monkeypatch.setattr(seed, "add_revision", injected_failure)
    with pytest.raises(RuntimeError, match="Injected import failure"):
        await client.post(ROOT + "/seed-references", headers=admin)
    async with app.state.sessions() as db:
        assert await db.scalar(select(func.count()).select_from(WikiPage)) == before


async def test_import_does_not_create_overdeep_sections(api):
    from uuid import uuid4, uuid5

    from sqlalchemy import select

    from vowen.modules.wiki.models import WikiSection
    from vowen.modules.wiki.seed import NAMESPACE

    client, app, admin, _, a, _, _, _, _ = await wiki_setup(api)
    async with app.state.sessions.begin() as db:
        await seed_references(db)
        parent = a
        for depth in range(2, 8):
            node = WikiSection(uid=uuid4(), parent_uid=parent, title=f"Depth{depth}")
            db.add(node)
            await db.flush()
            parent = node.uid
        db.add(WikiSection(uid=uuid5(NAMESPACE, "practices"), parent_uid=parent, title="Practices"))
    response = await client.post(ROOT + "/seed-references", headers=admin)
    assert response.status_code == 422
    async with app.state.sessions() as db:
        # Failed import rolls back every proposed child section.
        assert len(list(await db.scalars(select(WikiSection)))) == 9


async def test_section_only_import_advances_tree_version(api):
    from vowen.modules.references.models import PracticeCategory

    client, app, admin, _, _, _, _, _, _ = await wiki_setup(api)
    async with app.state.sessions.begin() as db:
        await seed_references(db)
    assert (await client.post(ROOT + "/seed-references", headers=admin)).status_code == 200
    before = (await client.get("/api/v1/wiki/tree", headers=admin)).json()["version"]
    async with app.state.sessions.begin() as db:
        db.add(PracticeCategory(name="Empty category"))
    result = await client.post(ROOT + "/seed-references", headers=admin)
    assert result.json()["created"] == 0
    assert (await client.get("/api/v1/wiki/tree", headers=admin)).json()["version"] == before + 1
