import asyncio
from uuid import uuid4

from test_sessions import auth, login, provision
from test_telegram_validation import signed

SCHEMA = {
    "title": "Private survey",
    "questions": [{"id": "q", "label": "Question", "kind": "long_text", "required": True}],
}


async def setup_forms(api):
    client, app = api
    from vowen.core.crypto import init_keyring

    init_keyring(app.state.settings.data_keyring_file)
    ids = [await provision(app, 100000000001 + i) for i in range(3)]
    headers = [auth((await login(client, signed(100000000001 + i))).json()) for i in range(3)]
    response = await client.post("/api/v1/forms", headers=headers[0], json=SCHEMA)
    assert response.status_code == 200
    return client, app, ids, headers, response.json()


async def test_immutable_publication_and_concurrent_version_edit(api):
    c, app, ids, h, f = await setup_forms(api)
    path = "/api/v1/forms/" + f["id"]
    assert (await c.get(path, headers=h[1])).status_code == 404
    edited = await asyncio.gather(
        *[
            c.patch(path, headers=h[0], json={"expected_version": 1, "schema_body": SCHEMA})
            for _ in range(2)
        ]
    )
    assert sorted(r.status_code for r in edited) == [200, 409]
    assert (
        await c.post(path + "/publish", headers=h[0], json={"expected_version": 2})
    ).status_code == 200
    assert (
        await c.patch(path, headers=h[0], json={"expected_version": 3, "schema_body": SCHEMA})
    ).status_code == 409
    revised = await c.post(
        path + "/versions",
        headers=h[0],
        json={"expected_version": 3, "schema_body": {**SCHEMA, "title": "Next"}},
    )
    assert revised.status_code == 200
    assert revised.json()["version_id"] != f["version_id"]


async def test_internal_recipient_private_draft_snapshot_and_withdrawal(api):
    c, app, ids, h, f = await setup_forms(api)
    p = "/api/v1/forms/" + f["id"]
    await c.post(p + "/publish", headers=h[0], json={"expected_version": 1})
    invite = (
        await c.post(
            p + "/invitations",
            headers=h[0],
            json={"recipient_user_id": str(ids[1]), "reader_ids": [str(ids[2])]},
        )
    ).json()
    ip = "/api/v1/form-invitations/" + invite["id"]
    assert (await c.get(ip, headers=h[0])).status_code == 404
    assert (await c.get(ip, headers=h[2])).status_code == 404
    assert (
        await c.put(ip + "/draft", headers=h[1], json={"answers": {"q": "secret answer"}})
    ).status_code == 200
    assert (await c.get("/api/v1/form-submissions", headers=h[2])).json() == []
    body = {
        "answers": {"q": "secret answer"},
        "idempotency_key": str(uuid4()),
        "acknowledged": True,
    }
    result = await asyncio.gather(
        *[c.post(ip + "/submit", headers=h[1], json=body) for _ in range(2)]
    )
    assert [r.status_code for r in result] == [200, 200]
    sid = result[0].json()["id"]
    assert result[1].json()["id"] == sid
    assert (await c.get("/api/v1/form-submissions", headers=h[0])).json() == []
    assert (await c.get("/api/v1/form-submissions/" + sid, headers=h[2])).json()["answers"] == {
        "q": "secret answer"
    }
    assert (await c.delete("/api/v1/form-submissions/" + sid, headers=h[2])).status_code == 404
    assert (await c.delete("/api/v1/form-submissions/" + sid, headers=h[1])).status_code == 204
    assert (await c.get("/api/v1/form-submissions/" + sid, headers=h[2])).status_code == 404
