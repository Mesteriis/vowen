from uuid import uuid4

from sqlalchemy import select
from test_wiki_read import wiki_setup

ROOT = "/api/v1/wiki/admin"


def doc(section, title="New", body="New body"):
    return dict(section_uid=str(section), title=title, summary="", body=body)


async def create(client, admin, section):
    response = await client.post(
        ROOT + "/pages", headers=admin, json={"kind": "article", "document": doc(section)}
    )
    assert response.status_code == 200, response.text
    return response.json()


async def test_admin_cycle_preserves_publication_and_rejects_conflicts(api):
    client, _, admin, member, a, b, _, _, _ = await wiki_setup(api)
    page = await create(client, admin, a)
    uid = page["uid"]
    public = f"/api/v1/wiki/pages/{uid}"
    assert (await client.get(public, headers=member)).status_code == 404
    response = await client.post(
        ROOT + f"/pages/{uid}/publish",
        headers=admin,
        json={"expected_version": page["version"], "revision_uid": page["draft_revision_uid"]},
    )
    assert response.status_code == 200, response.text
    page = response.json()
    assert (await client.get(public, headers=member)).json()["document"]["title"] == "New"
    saved = await client.patch(
        ROOT + f"/pages/{uid}",
        headers=admin,
        json={"expected_version": page["version"], "document": doc(b, "Changed")},
    )
    assert saved.status_code == 200
    assert (await client.get(public, headers=member)).json()["document"]["title"] == "New"
    assert (
        await client.patch(
            ROOT + f"/pages/{uid}",
            headers=admin,
            json={"expected_version": page["version"], "document": doc(b)},
        )
    ).status_code == 409
    page = saved.json()
    for archived in [True, False]:
        response = await client.post(
            ROOT + f"/pages/{uid}/archive",
            headers=admin,
            json={"expected_version": page["version"], "archived": archived},
        )
        assert response.status_code == 200
        page = response.json()
        assert (await client.get(public, headers=member)).status_code == (404 if archived else 200)
    history = await client.get(ROOT + f"/pages/{uid}/revisions", headers=admin)
    assert len(history.json()) == 2


async def test_all_admin_routes_deny_member_and_lost_admin(api):
    client, app, admin, member, a, _, p, _, _ = await wiki_setup(api)
    for method, path, payload in [
        ("get", "/pages", None),
        ("get", f"/pages/{p}", None),
        ("get", f"/pages/{p}/revisions", None),
        ("get", f"/pages/{p}/revisions/{uuid4()}", None),
        ("post", "/pages", {"kind": "article", "document": doc(a)}),
        ("patch", f"/pages/{p}", {"expected_version": 1, "document": doc(a)}),
        ("post", f"/pages/{p}/publish", {"expected_version": 1, "revision_uid": str(uuid4())}),
        ("post", f"/pages/{p}/archive", {"expected_version": 1, "archived": True}),
        ("post", "/sections", {"title": "X", "expected_tree_version": 1}),
        (
            "patch",
            f"/sections/{a}",
            {"title": "X", "expected_tree_version": 1, "expected_version": 1},
        ),
        ("delete", f"/sections/{a}?expected_version=1&expected_tree_version=1", None),
    ]:
        kwargs = {"headers": member}
        if payload is not None:
            kwargs["json"] = payload
        response = await client.request(method, ROOT + path, **kwargs)
        assert response.status_code == 403, (path, response.text)
    from vowen.modules.identity.models import User

    async with app.state.sessions.begin() as db:
        owner = await db.scalar(select(User).where(User.is_admin))
        owner.is_admin = False
    assert (
        await client.post(
            ROOT + "/pages", headers=admin, json={"kind": "article", "document": doc(a)}
        )
    ).status_code == 403


async def test_section_cycles_depth_and_nonempty_deletion(api):
    client, _, admin, _, a, _, _, _, _ = await wiki_setup(api)
    parent = str(a)
    tree_version = 1
    first = None
    for depth in range(2, 10):
        r = await client.post(
            ROOT + "/sections",
            headers=admin,
            json={
                "title": f"Level {depth}",
                "parent_uid": parent,
                "expected_tree_version": tree_version,
            },
        )
        if depth == 9:
            assert r.status_code == 422
            break
        assert r.status_code == 200, r.text
        tree = r.json()
        row = next(s for s in tree["sections"] if s["title"] == f"Level {depth}")
        first = first or row
        parent, tree_version = row["uid"], tree["version"]
    r = await client.patch(
        ROOT + f"/sections/{a}",
        headers=admin,
        json={
            "title": "Cycle",
            "parent_uid": parent,
            "expected_version": 1,
            "expected_tree_version": tree_version,
        },
    )
    assert r.status_code == 422
    assert (
        await client.delete(
            ROOT + f"/sections/{a}",
            headers=admin,
            params={"expected_version": 1, "expected_tree_version": tree_version},
        )
    ).status_code == 409


async def test_public_snapshot_does_not_change_after_draft_save(api):
    client, _, admin, member, a, b, _, _, _ = await wiki_setup(api)
    page = await create(client, admin, a)
    page = (
        await client.post(
            ROOT + f"/pages/{page['uid']}/publish",
            headers=admin,
            json={"expected_version": page["version"], "revision_uid": page["draft_revision_uid"]},
        )
    ).json()
    url = f"/api/v1/wiki/pages/{page['uid']}"
    before = (await client.get(url, headers=member)).json()
    assert (
        await client.patch(
            ROOT + f"/pages/{page['uid']}",
            headers=admin,
            json={"expected_version": page["version"], "document": doc(b, "Hidden title")},
        )
    ).status_code == 200
    assert (await client.get(url, headers=member)).json() == before
