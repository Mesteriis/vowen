from uuid import uuid4

from test_relations import accept, members, propose
from test_sessions import auth


async def test_selected_direct_reader_only_pause_and_private_draft(api):
    c, app = api
    ids, tokens = await members(c, app)
    relation = (await propose(c, tokens[0], ids[0], ids[1])).json()
    relation = (await accept(c, tokens[0], relation)).json()
    relation = (await accept(c, tokens[1], relation)).json()
    second = (await propose(c, tokens[1], ids[1], ids[2])).json()
    second = (await accept(c, tokens[1], second)).json()
    await accept(c, tokens[2], second)
    h = auth(tokens[0])
    draft = await c.put(
        "/api/v1/me/profile/draft",
        headers=h,
        json={
            "expected_version": 0,
            "section": "health",
            "value": {"notes": "OWNER HEALTH"},
            "step": 5,
        },
    )
    assert draft.status_code == 200
    draft = await c.put(
        "/api/v1/me/profile/draft",
        headers=h,
        json={
            "expected_version": draft.json()["version"],
            "section": "identity",
            "value": {"display_name": "Owner", "bio": "Shared biography"},
            "step": 1,
        },
    )
    draft = await c.put(
        "/api/v1/me/profile/draft",
        headers=h,
        json={
            "expected_version": draft.json()["version"],
            "section": "visibility",
            "value": {"sections": [{"section": "identity", "reader_ids": [str(ids[1])]}]},
            "step": 6,
        },
    )
    assert draft.status_code == 200, draft.text
    published = await c.post(
        "/api/v1/me/profile/publish",
        headers=h,
        json={"expected_draft_version": draft.json()["version"]},
    )
    assert published.status_code == 200, published.text
    path = f"/api/v1/participants/{ids[0]}/profile"
    assert (await c.get(path)).status_code == 401
    shared = (await c.get(path, headers=auth(tokens[1]))).json()
    assert set(shared) == {"owner_id", "sections"}
    assert set(shared["sections"]) == {"identity"}
    assert shared["sections"]["identity"]["bio"] == "Shared biography"
    from vowen.modules.identity.models import User

    async with app.state.sessions.begin() as db:
        administrator = await db.get(User, ids[2])
        dominant = await db.get(User, ids[3])
        administrator.is_admin = True
        dominant.shop_role = "dominant"
    for viewer in (2, 3):
        assert (await c.get(path, headers=auth(tokens[viewer]))).status_code == 404
    assert (
        await c.get(f"/api/v1/participants/{uuid4()}/profile", headers=auth(tokens[1]))
    ).status_code == 404
    assert "OWNER HEALTH" not in str(
        (await c.get("/api/v1/participants", headers=auth(tokens[1]))).json()
    )
    # No draft belongs to the reader, regardless of their relation or administration role.
    assert (await c.get("/api/v1/me/profile/draft", headers=auth(tokens[1]))).status_code == 404
    await c.post(
        f"/api/v1/relations/{relation['id']}/pause",
        headers=auth(tokens[1]),
        json={"expected_version": relation["version"]},
    )
    assert (await c.get(path, headers=auth(tokens[1]))).status_code == 404
    stale = await c.put(
        "/api/v1/me/profile/draft", headers=h, json={"expected_version": 0, "step": 6}
    )
    assert stale.status_code == 200
    assert (
        await c.post(
            "/api/v1/me/profile/publish",
            headers=h,
            json={"expected_draft_version": stale.json()["version"]},
        )
    ).status_code == 422
    recovered = await c.put(
        "/api/v1/me/profile/draft",
        headers=h,
        json={
            "expected_version": stale.json()["version"],
            "section": "visibility",
            "value": {"sections": []},
            "step": 6,
        },
    )
    assert recovered.status_code == 200
    assert (
        await c.post(
            "/api/v1/me/profile/publish",
            headers=h,
            json={"expected_draft_version": recovered.json()["version"]},
        )
    ).status_code == 200


async def test_limits_projection_and_new_relation_does_not_restore_old_grant(api):
    from vowen.modules.references.models import Practice

    c, app = api
    ids, tokens = await members(c, app, 2)
    uid = uuid4()
    async with app.state.sessions.begin() as db:
        db.add(Practice(uid=uid, name="Synthetic limit"))
    relation = (await propose(c, tokens[0], ids[0], ids[1])).json()
    relation = (await accept(c, tokens[0], relation)).json()
    relation = (await accept(c, tokens[1], relation)).json()
    h = auth(tokens[0])
    path = f"/api/v1/participants/{ids[0]}/profile"
    draft = (
        await c.put(
            "/api/v1/me/profile/draft",
            headers=h,
            json={
                "expected_version": 0,
                "section": "preferences",
                "value": {
                    "practices": [
                        {
                            "practice_uid": str(uid),
                            "attitude": "taboo",
                            "experience": "experienced",
                            "conditions": "Private condition",
                        }
                    ]
                },
                "step": 3,
            },
        )
    ).json()
    draft = (
        await c.put(
            "/api/v1/me/profile/draft",
            headers=h,
            json={
                "expected_version": draft["version"],
                "section": "visibility",
                "value": {"sections": [{"section": "boundaries", "reader_ids": [str(ids[1])]}]},
                "step": 6,
            },
        )
    ).json()
    assert (
        await c.post(
            "/api/v1/me/profile/publish",
            headers=h,
            json={"expected_draft_version": draft["version"]},
        )
    ).status_code == 200
    shared = (await c.get(path, headers=auth(tokens[1]))).json()
    assert shared["sections"]["boundaries"]["practices"] == [
        {"practice_uid": str(uid), "attitude": "taboo", "conditions": "Private condition"}
    ]
    assert "experience" not in str(shared)
    await c.post(
        f"/api/v1/relations/{relation['id']}/revoke",
        headers=h,
        json={"expected_version": relation["version"]},
    )
    new = (await propose(c, tokens[0], ids[0], ids[1])).json()
    new = (await accept(c, tokens[0], new)).json()
    await accept(c, tokens[1], new)
    assert (await c.get(path, headers=auth(tokens[1]))).status_code == 404
