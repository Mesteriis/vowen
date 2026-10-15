import asyncio

from sqlalchemy import text
from test_relations import accept, members, propose
from test_sessions import auth


async def setup_rule(api):
    client, app = api
    ids, tokens = await members(client, app, 4)
    for target in (1, 2):
        relation = (await propose(client, tokens[0], ids[0], ids[target])).json()
        relation = (await accept(client, tokens[0], relation)).json()
        assert (await accept(client, tokens[target], relation)).status_code == 200
    response = await client.post(
        "/api/v1/rules",
        headers=auth(tokens[0]),
        json={"title": "Synthetic rule", "description": "sensitive-rule-content"},
    )
    assert response.status_code == 200
    rule = response.json()
    rule = (
        await client.post(
            f"/api/v1/rules/{rule['id']}/publish",
            headers=auth(tokens[0]),
            json={"expected_version": rule["revision"]},
        )
    ).json()
    return client, app, ids, tokens, rule


async def assign(client, token, rule, target, managers):
    return await client.post(
        f"/api/v1/rules/{rule['id']}/assignments",
        headers=auth(token),
        json={
            "rule_version_id": rule["version_id"],
            "recipient_id": str(target),
            "manager_ids": [str(x) for x in managers],
        },
    )


async def action(client, token, assignment, name):
    return await client.post(
        f"/api/v1/rule-assignments/{assignment['id']}/{name}",
        headers=auth(token),
        json={
            "expected_version": assignment["revision"],
            "rule_version_id": assignment["rule_version_id"],
        },
    )


async def test_per_recipient_exact_version_and_replacement(api):
    client, app, ids, tokens, rule = await setup_rule(api)
    b = (await assign(client, tokens[0], rule, ids[1], [ids[0]])).json()
    c = (await assign(client, tokens[0], rule, ids[2], [ids[0]])).json()
    assert b["status"] == c["status"] == "pending_acceptance"
    b = (await action(client, tokens[1], b, "accept")).json()
    assert b["status"] == "active" and b["accepted_at"] is not None
    assert (await action(client, tokens[2], c, "decline")).json()["status"] == "revoked"
    assert (await client.get("/api/v1/rule-assignments", headers=auth(tokens[3]))).json() == []
    assert (await action(client, tokens[0], b, "accept")).status_code == 403
    assert (
        await client.patch(
            f"/api/v1/rules/{rule['id']}",
            headers=auth(tokens[0]),
            json={"expected_version": rule["revision"], "title": "Mutated", "description": "no"},
        )
    ).status_code == 409
    newer = (
        await client.post(
            f"/api/v1/rules/{rule['id']}/versions",
            headers=auth(tokens[0]),
            json={
                "expected_version": rule["revision"],
                "title": "New rule",
                "description": "new-sensitive-rule",
            },
        )
    ).json()
    assert (await assign(client, tokens[0], newer, ids[1], [ids[0]])).status_code == 409
    newer = (
        await client.post(
            f"/api/v1/rules/{rule['id']}/publish",
            headers=auth(tokens[0]),
            json={"expected_version": newer["revision"]},
        )
    ).json()
    pending = (await assign(client, tokens[0], newer, ids[1], [ids[0]])).json()
    history = (await client.get("/api/v1/rule-assignments", headers=auth(tokens[1]))).json()
    assert next(x for x in history if x["id"] == b["id"])["status"] == "active"
    wrong = dict(pending, rule_version_id=rule["version_id"])
    assert (await action(client, tokens[1], wrong, "accept")).status_code == 409
    outcomes = await asyncio.gather(
        *(action(client, tokens[1], pending, "accept") for _ in range(2))
    )
    assert sorted(x.status_code for x in outcomes) == [200, 409]
    history = (await client.get("/api/v1/rule-assignments", headers=auth(tokens[1]))).json()
    assert sum(x["status"] == "active" for x in history) == 1
    assert next(x for x in history if x["id"] == b["id"])["accepted_at"] == b["accepted_at"]
    async with app.state.engine.connect() as conn:
        payloads = (
            (await conn.execute(text("SELECT ciphertext FROM rule_versions"))).scalars().all()
        )
        assert len(payloads) == 2 and all(b"sensitive-rule" not in bytes(x) for x in payloads)


async def test_explicit_manager_acl_pause_archive_and_history(api):
    client, app, ids, tokens, rule = await setup_rule(api)
    assert (await assign(client, tokens[0], rule, ids[1], [ids[3]])).status_code == 403
    a = (await assign(client, tokens[0], rule, ids[1], [])).json()
    # Author is not implicitly a manager and cannot list/read this assignment.
    assert (await client.get("/api/v1/rule-assignments", headers=auth(tokens[0]))).json() == []
    assert (await action(client, tokens[0], a, "pause")).status_code == 404
    assert (await assign(client, tokens[0], rule, ids[1], [])).status_code == 409
    a = (await action(client, tokens[1], a, "accept")).json()
    archived = await client.post(
        f"/api/v1/rules/{rule['id']}/archive",
        headers=auth(tokens[0]),
        json={"expected_version": rule["revision"]},
    )
    assert archived.status_code == 200
    assert (await assign(client, tokens[0], rule, ids[2], [ids[0]])).status_code == 409
    assert (await client.post("/api/v1/me/pause", headers=auth(tokens[1]))).status_code == 204
    history = (await client.get("/api/v1/rule-assignments", headers=auth(tokens[1]))).json()
    assert history[0]["status"] == "active" and history[0]["effective"] is False
    a = (await action(client, tokens[1], a, "pause")).json()
    assert a["status"] == "paused"
    assert (await action(client, tokens[1], a, "revoke")).json()["status"] == "revoked"


async def test_manager_revocation_filters_reads_and_concurrent_assignment(api):
    client, app, ids, tokens, rule = await setup_rule(api)
    results = await asyncio.gather(
        *(assign(client, tokens[0], rule, ids[1], [ids[0]]) for _ in range(2))
    )
    assert sorted(r.status_code for r in results) == [200, 409]
    a = next(r.json() for r in results if r.status_code == 200)
    assert len((await client.get("/api/v1/rule-assignments", headers=auth(tokens[0]))).json()) == 1
    await client.post("/api/v1/me/pause", headers=auth(tokens[1]))
    assert (await client.get("/api/v1/rule-assignments", headers=auth(tokens[0]))).json() == []
    assert (await action(client, tokens[1], a, "accept")).status_code == 403
    assert (await action(client, tokens[1], a, "decline")).status_code == 200


async def test_author_version_history_is_separate_from_recipient_acl(api):
    client, app, ids, tokens, rule = await setup_rule(api)
    path = f"/api/v1/rules/{rule['id']}/versions"
    response = await client.get(path, headers=auth(tokens[0]))
    assert response.status_code == 200
    assert response.json()[0]["version_id"] == rule["version_id"]
    assert (await client.get(path, headers=auth(tokens[1]))).status_code == 404
    edited = await client.post(
        path,
        headers=auth(tokens[0]),
        json={"expected_version": rule["revision"], "title": "Second", "description": "Next draft"},
    )
    assert edited.status_code == 200
    history = (await client.get(path, headers=auth(tokens[0]))).json()
    assert {x["status"] for x in history} == {"draft", "published"}
    assert {x["description"] for x in history} == {"Next draft", "sensitive-rule-content"}
