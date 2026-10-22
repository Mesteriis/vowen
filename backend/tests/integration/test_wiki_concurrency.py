import asyncio

from test_wiki_admin import ROOT, create, doc
from test_wiki_read import wiki_setup


async def test_two_saves_same_version_have_one_winner(api):
    client, _, admin, _, a, _, _, _, _ = await wiki_setup(api)
    p = await create(client, admin, a)
    responses = await asyncio.gather(
        *[
            client.patch(
                ROOT + f"/pages/{p['uid']}",
                headers=admin,
                json={"expected_version": p["version"], "document": doc(a, title)},
            )
            for title in ["First edit", "Second edit"]
        ]
    )
    assert sorted(r.status_code for r in responses) == [200, 409]


async def test_cross_moves_do_not_create_cycle(api):
    client, _, admin, _, a, b, _, _, _ = await wiki_setup(api)
    results = await asyncio.gather(
        *[
            client.patch(
                ROOT + f"/sections/{uid}",
                headers=admin,
                json={
                    "title": "Moved",
                    "parent_uid": str(parent),
                    "expected_version": 1,
                    "expected_tree_version": 1,
                },
            )
            for uid, parent in [(a, b), (b, a)]
        ]
    )
    assert sorted(r.status_code for r in results) == [200, 409]


async def test_publish_and_save_never_substitute_the_target_revision(api):
    client, _, admin, member, a, _, _, _, _ = await wiki_setup(api)
    page = await create(client, admin, a)
    responses = await asyncio.gather(
        client.patch(
            ROOT + f"/pages/{page['uid']}",
            headers=admin,
            json={"expected_version": page["version"], "document": doc(a, "New private draft")},
        ),
        client.post(
            ROOT + f"/pages/{page['uid']}/publish",
            headers=admin,
            json={"expected_version": page["version"], "revision_uid": page["draft_revision_uid"]},
        ),
    )
    assert sorted(r.status_code for r in responses) == [200, 409]
    public = await client.get("/api/v1/wiki/pages/" + page["uid"], headers=member)
    if responses[1].status_code == 200:
        assert public.json()["document"]["title"] == "New"
    else:
        assert public.status_code == 404


async def test_revocation_wins_against_waiting_writer(api):
    from sqlalchemy import select

    from vowen.modules.identity.models import AdministrationState, User

    client, app, admin, _, a, _, _, _, _ = await wiki_setup(api)
    async with app.state.sessions() as db:
        async with db.begin():
            await db.get(AdministrationState, 1, with_for_update=True)
            owner = await db.scalar(select(User).where(User.is_admin))
            owner.is_admin = False
            task = asyncio.create_task(
                client.post(
                    ROOT + "/pages",
                    headers=admin,
                    json={"kind": "article", "document": doc(a, "Denied writer")},
                )
            )
            await asyncio.sleep(0.05)
            assert not task.done()
        response = await task
    assert response.status_code == 403
