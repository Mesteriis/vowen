from uuid import uuid4

from test_administration import setup_members


async def wiki_setup(api):
    client, app, owner, other, admin, member = await setup_members(api)
    from vowen.modules.wiki.models import WikiPage, WikiRevision, WikiSection, WikiTreeState

    a, b, p, published, draft, hidden, archived = [uuid4() for _ in range(7)]
    async with app.state.sessions.begin() as db:
        db.add(WikiTreeState(id=1, version=1))
        db.add_all([WikiSection(uid=a, title="First"), WikiSection(uid=b, title="Second")])
        db.add_all(
            [
                WikiPage(uid=p, kind="article"),
                WikiPage(uid=hidden, kind="article"),
                WikiPage(uid=archived, kind="article"),
            ]
        )
        await db.flush()
        db.add_all(
            [
                WikiRevision(
                    uid=published,
                    page_uid=p,
                    section_uid=a,
                    title="Visible",
                    body="Published body",
                    author_id=owner,
                ),
                WikiRevision(
                    uid=draft,
                    page_uid=p,
                    section_uid=b,
                    title="Secret draft",
                    body="Private draft",
                    author_id=owner,
                ),
            ]
        )
        await db.flush()
        page = await db.get(WikiPage, p)
        page.published_revision_uid, page.draft_revision_uid = published, draft
    return client, app, admin, member, a, b, p, hidden, archived


async def test_published_projection_never_uses_draft(api):
    client, _, _, member, a, b, p, hidden, archived = await wiki_setup(api)
    root = "/api/v1/wiki"
    assert (await client.get(root + "/tree")).status_code == 401
    response = await client.get(root + "/tree", headers=member)
    assert response.status_code == 200
    tree = response.json()
    assert len(tree["sections"]) == 2 and len(tree["pages"]) == 1
    assert tree["pages"][0]["title"] == "Visible"
    assert tree["pages"][0]["section_uid"] == str(a)
    page = (await client.get(root + f"/pages/{p}", headers=member)).json()
    assert page["document"]["body"] == "Published body"
    assert "Secret" not in str(page)
    for q, total in [("Secret", 0), ("Published", 1), ("%", 0), ("", 1)]:
        result = await client.get(root + "/search", params={"q": q}, headers=member)
        assert result.status_code == 200 and result.json()["total"] == total
    for uid in [hidden, archived, uuid4()]:
        assert (await client.get(root + f"/pages/{uid}", headers=member)).status_code == 404
    assert (
        await client.get(root + "/search", params={"q": "x" * 201}, headers=member)
    ).status_code == 422
    assert (
        await client.get(root + "/search", params={"limit": 51}, headers=member)
    ).status_code == 422
