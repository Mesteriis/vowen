import asyncio
from uuid import uuid4

from test_sessions import auth, login, provision


async def setup_profile(api):
    client, app = api
    owner = await provision(app)
    tokens = (await login(client)).json()
    return client, app, owner, auth(tokens)


async def test_draft_resume_without_publish(api):
    c, _, _, h = await setup_profile(api)
    initial = await c.get("/api/v1/me/profile", headers=h)
    assert initial.status_code == 200
    assert initial.json()["version"] == 0
    saved = await c.put(
        "/api/v1/me/profile/draft",
        headers=h,
        json={
            "expected_version": 0,
            "section": "identity",
            "value": {"display_name": "New", "bio": "Private draft"},
            "step": 2,
        },
    )
    assert saved.status_code == 200, saved.text
    assert (await c.get("/api/v1/me/profile/draft", headers=h)).json()["document"]["identity"][
        "bio"
    ] == "Private draft"
    assert (await c.get("/api/v1/me", headers=h)).json()["display_name"] == "Synthetic"
    assert (await c.get("/api/v1/me/profile", headers=h)).json()["document"]["identity"][
        "bio"
    ] == ""
    resumed = await c.put(
        "/api/v1/me/profile/draft",
        headers=h,
        json={"expected_version": saved.json()["version"], "step": 5, "deferred": True},
    )
    assert resumed.json()["document"]["identity"]["bio"] == "Private draft"
    done = await c.post(
        "/api/v1/me/profile/publish",
        headers=h,
        json={"expected_draft_version": resumed.json()["version"]},
    )
    assert done.status_code == 200, done.text
    assert done.json()["version"] == 1
    assert (await c.get("/api/v1/me", headers=h)).json()["display_name"] == "New"
    assert (await c.get("/api/v1/me/profile/draft", headers=h)).status_code == 404
    assert (
        await c.post(
            "/api/v1/me/profile/publish",
            headers=h,
            json={"expected_draft_version": resumed.json()["version"]},
        )
    ).status_code == 409


async def test_stale_account_and_concurrent_draft(api):
    c, _, _, h = await setup_profile(api)
    saved = (
        await c.put("/api/v1/me/profile/draft", headers=h, json={"expected_version": 0, "step": 1})
    ).json()
    assert "version" in saved
    replies = await asyncio.gather(
        *[
            c.put(
                "/api/v1/me/profile/draft",
                headers=h,
                json={"expected_version": saved["version"], "step": step},
            )
            for step in [2, 3]
        ]
    )
    assert sorted(r.status_code for r in replies) == [200, 409]
    version = next(r.json()["version"] for r in replies if r.status_code == 200)
    await c.patch(
        "/api/v1/me/preferences",
        headers=h,
        json={"expected_version": 1, "display_name": "Other edit"},
    )
    assert (
        await c.post(
            "/api/v1/me/profile/publish", headers=h, json={"expected_draft_version": version}
        )
    ).status_code == 409
    assert (await c.get("/api/v1/me", headers=h)).json()["display_name"] == "Other edit"


async def test_unknown_wrong_kind_duplicate_uuid_rejected(api):
    from vowen.modules.references.models import Gender, Practice

    c, app, _, h = await setup_profile(api)
    uid, practice = uuid4(), uuid4()
    async with app.state.sessions.begin() as db:
        db.add(Gender(uid=uid, name="Gender"))
        db.add(Practice(uid=practice, name="Practice"))
    for ids in [[str(uuid4())], [str(uid)], [str(practice), str(practice)]]:
        response = await c.put(
            "/api/v1/me/profile/draft",
            headers=h,
            json={
                "expected_version": 0,
                "section": "health",
                "value": {"care_practice_uids": ids},
                "step": 5,
            },
        )
        assert response.status_code == 422, response.text
    assert (await c.get("/api/v1/me/profile", headers=h)).json()["version"] == 0


async def test_omitted_section_fields_preserve_and_explicit_clear_removes(api):
    from vowen.modules.references.models import Allergen

    c, app, _, h = await setup_profile(api)
    uid = uuid4()
    async with app.state.sessions.begin() as db:
        db.add(Allergen(uid=uid, name="Synthetic allergen"))
    draft = (
        await c.put(
            "/api/v1/me/profile/draft",
            headers=h,
            json={
                "expected_version": 0,
                "section": "health",
                "value": {"allergen_uids": [str(uid)], "notes": "First"},
                "step": 5,
            },
        )
    ).json()
    changed = await c.put(
        "/api/v1/me/profile/draft",
        headers=h,
        json={
            "expected_version": draft["version"],
            "section": "health",
            "value": {"notes": "Updated"},
            "step": 5,
        },
    )
    assert changed.json()["document"]["health"]["allergen_uids"] == [str(uid)]
    cleared = await c.put(
        "/api/v1/me/profile/draft",
        headers=h,
        json={
            "expected_version": changed.json()["version"],
            "section": "health",
            "value": {"allergen_uids": []},
            "step": 5,
        },
    )
    assert cleared.json()["document"]["health"]["allergen_uids"] == []
    assert cleared.json()["document"]["health"]["notes"] == "Updated"
