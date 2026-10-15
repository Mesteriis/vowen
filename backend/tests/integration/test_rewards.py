import asyncio
from uuid import uuid4

from test_relations import accept
from test_ritual_review import setup_ritual
from test_sessions import auth


async def reward_setup(api):
    client, app, ids, tokens, ritual, a, o = await setup_ritual(api)
    relation = (await client.get("/api/v1/relations", headers=auth(tokens[0]))).json()[0]
    relation = (
        await client.post(
            f"/api/v1/relations/{relation['id']}/versions",
            headers=auth(tokens[0]),
            json={
                "expected_version": relation["version"],
                "agreement_text": "Explicit reward authority",
                "scopes": ["rituals.assign", "rituals.review", "rewards.grant"],
            },
        )
    ).json()
    relation = (await accept(client, tokens[0], relation)).json()
    assert (await accept(client, tokens[1], relation)).status_code == 200
    created = await client.post(
        "/api/v1/rewards",
        headers=auth(tokens[0]),
        json={
            "title": "Quiet evening",
            "description": "Choose an evening activity",
            "conditions": "By agreement",
        },
    )
    assert created.status_code == 200
    return client, app, ids, tokens, ritual, created.json()


async def test_manual_reward_lifecycle_history_acl_and_retry(api):
    client, app, ids, tokens, ritual, reward = await reward_setup(api)
    body = {
        "reward_version_id": reward["version_id"],
        "recipient_id": str(ids[1]),
        "idempotency_key": str(uuid4()),
    }
    responses = await asyncio.gather(
        *(
            client.post("/api/v1/reward-grants", headers=auth(tokens[0]), json=body)
            for _ in range(2)
        )
    )
    assert [r.status_code for r in responses] == [200, 200]
    g = responses[0].json()
    assert g["id"] == responses[1].json()["id"] and g["status"] == "offered"
    assert (await client.get("/api/v1/reward-grants", headers=auth(tokens[3]))).json() == []
    path = f"/api/v1/reward-grants/{g['id']}/transitions"
    assert (
        await client.post(
            path,
            headers=auth(tokens[0]),
            json={"expected_version": g["revision"], "action": "accept"},
        )
    ).status_code == 403
    accepted = await client.post(
        path, headers=auth(tokens[1]), json={"expected_version": g["revision"], "action": "accept"}
    )
    assert accepted.status_code == 200
    g = accepted.json()
    delivered = await client.post(
        path, headers=auth(tokens[0]), json={"expected_version": g["revision"], "action": "deliver"}
    )
    assert delivered.status_code == 200 and [h["status"] for h in delivered.json()["history"]] == [
        "offered",
        "accepted",
        "delivered",
    ]
    assert (
        await client.post(
            path,
            headers=auth(tokens[0]),
            json={"expected_version": delivered.json()["revision"], "action": "cancel"},
        )
    ).status_code == 409
    await client.post("/api/v1/me/pause", headers=auth(tokens[1]))
    assert (await client.get("/api/v1/reward-grants", headers=auth(tokens[1]))).json()[0][
        "status"
    ] == "delivered"


async def test_approved_occurrence_grants_once_and_freezes_policy_version(api):
    client, app, ids, tokens, ritual, reward = await reward_setup(api)
    body = {
        "idempotency_key": str(uuid4()),
        "recipient_id": str(ids[1]),
        "reviewer_ids": [str(ids[0]), str(ids[2])],
        "approval_required": True,
        "reward_version_id": reward["version_id"],
        "schedule": {
            "kind": "daily",
            "timezone": "UTC",
            "hour": 9,
            "minute": 0,
            "start_date": "2026-10-15",
        },
    }
    a = await client.post(
        f"/api/v1/rituals/{ritual['id']}/assignments", headers=auth(tokens[0]), json=body
    )
    assert a.status_code == 200
    a = a.json()
    o = next(
        x
        for x in (await client.get("/api/v1/ritual-occurrences", headers=auth(tokens[1]))).json()
        if x["assignment_id"] == a["id"]
    )
    path = f"/api/v1/ritual-occurrences/{o['id']}"
    command = {
        "expected_version": o["revision"],
        "idempotency_key": str(uuid4()),
        "text": "Completed",
    }
    o = (await client.post(path + "/report", headers=auth(tokens[1]), json=command)).json()
    outcomes = await asyncio.gather(
        *(
            client.post(
                path + "/review",
                headers=auth(tokens[i]),
                json={"expected_version": o["revision"], "decision": "approved"},
            )
            for i in (0, 2)
        )
    )
    assert sorted(r.status_code for r in outcomes) == [200, 409]
    assert (
        await client.post(path + "/report", headers=auth(tokens[1]), json=command)
    ).status_code == 200
    grants = (await client.get("/api/v1/reward-grants", headers=auth(tokens[1]))).json()
    assert (
        len(grants) == 1
        and grants[0]["occurrence_id"] == o["id"]
        and grants[0]["reward_policy_id"] == a["reward_policy_id"]
    )
    await client.post("/api/v1/me/pause", headers=auth(tokens[1]))
    assert len((await client.get("/api/v1/reward-grants", headers=auth(tokens[1]))).json()) == 1


async def test_manual_grant_requires_direct_scope_and_no_review_autoapproval_grants(api):
    client, app, ids, tokens, ritual, reward = await reward_setup(api)
    assert (
        await client.post(
            "/api/v1/reward-grants",
            headers=auth(tokens[0]),
            json={
                "reward_version_id": reward["version_id"],
                "recipient_id": str(ids[3]),
                "idempotency_key": str(uuid4()),
            },
        )
    ).status_code == 403
    body = {
        "idempotency_key": str(uuid4()),
        "recipient_id": str(ids[1]),
        "reviewer_ids": [],
        "approval_required": False,
        "reward_version_id": reward["version_id"],
        "schedule": {
            "kind": "once",
            "timezone": "UTC",
            "hour": 9,
            "minute": 0,
            "start_date": "2026-10-15",
        },
    }
    a = (
        await client.post(
            f"/api/v1/rituals/{ritual['id']}/assignments", headers=auth(tokens[0]), json=body
        )
    ).json()
    o = next(
        x
        for x in (await client.get("/api/v1/ritual-occurrences", headers=auth(tokens[1]))).json()
        if x["assignment_id"] == a["id"]
    )
    response = await client.post(
        f"/api/v1/ritual-occurrences/{o['id']}/report",
        headers=auth(tokens[1]),
        json={
            "expected_version": o["revision"],
            "idempotency_key": str(uuid4()),
            "text": "Completed",
        },
    )
    assert response.status_code == 200
    grants = (await client.get("/api/v1/reward-grants", headers=auth(tokens[1]))).json()
    assert len(grants) == 1 and grants[0]["status"] == "offered"
