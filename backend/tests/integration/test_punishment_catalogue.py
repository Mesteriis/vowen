import asyncio
from uuid import uuid4

from test_discipline_transitions import setup
from test_sessions import auth


async def test_catalogue_separate_assignments_intensity_snapshot_and_isolation(api):
    c, app, ids, tokens, relations, _, _ = await setup(api)
    base = "/api/v1/punishment-templates"
    body = {
        "relation_id": relations[0]["id"],
        "title": "Synthetic variant",
        "description": "A stored variant",
        "conditions": "Stored conditions",
        "punishment_type": "physical",
        "device": "Рука",
        "body_part": "Руки",
        "strike_count": 1,
    }
    for actor, code in ((1, 403), (2, 404), (3, 404)):
        assert (await c.post(base, headers=auth(tokens[actor]), json=body)).status_code == code
    item = (await c.post(base, headers=auth(tokens[0]), json=body)).json()
    assert "intensity" not in item
    assert (
        await c.get(base, params={"relation_id": relations[0]["id"]}, headers=auth(tokens[2]))
    ).status_code == 404
    lower = (
        await c.get(base, params={"relation_id": relations[0]["id"]}, headers=auth(tokens[1]))
    ).json()
    assert len(lower) == 1 and not lower[0]["can_edit"]
    endpoint = f"{base}/{item['id']}/assign"
    command = {
        "expected_version": 1,
        "idempotency_key": str(uuid4()),
        "intensity": 2,
        "comment": "Typed comment",
    }
    assert (await c.post(endpoint, headers=auth(tokens[1]), json=command)).status_code == 403
    assert (await c.post(endpoint, headers=auth(tokens[2]), json=command)).status_code == 404
    invalid = {k: v for k, v in command.items() if k != "intensity"}
    assert (await c.post(endpoint, headers=auth(tokens[0]), json=invalid)).status_code == 422
    assert (
        await c.post(endpoint, headers=auth(tokens[0]), json={**command, "intensity": 11})
    ).status_code == 422
    results = await asyncio.gather(
        *(c.post(endpoint, headers=auth(tokens[0]), json=command) for _ in range(2))
    )
    assert all(r.status_code == 200 for r in results)
    assigned = results[0].json()
    assert assigned["id"] == results[1].json()["id"]
    assert assigned["status"] == "planned" and assigned["recipient_id"] == str(ids[1])
    snapshot = assigned["versions"][0]
    assert snapshot["intensity"] == 2 and snapshot["assignment_comment"] == "Typed comment"
    second = (
        await c.post(
            endpoint,
            headers=auth(tokens[0]),
            json={**command, "idempotency_key": str(uuid4()), "intensity": 8},
        )
    ).json()
    assert second["id"] != assigned["id"] and second["versions"][0]["intensity"] == 8
    edit = {k: v for k, v in body.items() if k != "relation_id"}
    changed = await c.patch(
        f"{base}/{item['id']}",
        headers=auth(tokens[0]),
        json={**edit, "expected_version": 1, "strike_count": 2},
    )
    assert changed.status_code == 200
    assert (
        await c.post(
            endpoint, headers=auth(tokens[0]), json={**command, "idempotency_key": str(uuid4())}
        )
    ).status_code == 409
    old = (
        await c.get(f"/api/v1/discipline-records/{assigned['id']}", headers=auth(tokens[1]))
    ).json()
    assert old["versions"][0]["strike_count"] == 1
    archived = await c.post(
        f"{base}/{item['id']}/archive", headers=auth(tokens[0]), json={"expected_version": 2}
    )
    assert archived.status_code == 204
    assert (
        await c.get(base, params={"relation_id": relations[0]["id"]}, headers=auth(tokens[0]))
    ).json() == []
    assert (
        await c.get(f"/api/v1/discipline-records/{assigned['id']}", headers=auth(tokens[1]))
    ).status_code == 200


async def test_rule_violation_uses_same_assignment_with_exact_rule_link(api):
    c, _, ids, tokens, relations, _, _ = await setup(api)
    base = "/api/v1/punishment-templates"
    template = (
        await c.post(
            base,
            headers=auth(tokens[0]),
            json={
                "relation_id": relations[0]["id"],
                "title": "Rule variant",
                "description": "Stored variant",
                "punishment_type": "physical",
                "device": "Рука",
                "body_part": "Руки",
                "strike_count": 1,
            },
        )
    ).json()
    rule = (
        await c.post(
            "/api/v1/rules",
            headers=auth(tokens[0]),
            json={"title": "Rule", "description": "A rule"},
        )
    ).json()
    rule = (
        await c.post(
            f"/api/v1/rules/{rule['id']}/publish",
            headers=auth(tokens[0]),
            json={"expected_version": rule["revision"]},
        )
    ).json()
    path = f"{base}/{template['id']}/assign"
    command = {
        "expected_version": 1,
        "idempotency_key": str(uuid4()),
        "intensity": 4,
        "rule_version_id": rule["version_id"],
        "comment": "Rule comment",
    }
    assert (await c.post(path, headers=auth(tokens[0]), json=command)).status_code == 403
    a = (
        await c.post(
            f"/api/v1/rules/{rule['id']}/assignments",
            headers=auth(tokens[0]),
            json={
                "rule_version_id": rule["version_id"],
                "recipient_id": str(ids[1]),
                "manager_ids": [str(ids[0])],
            },
        )
    ).json()
    assert (
        await c.post(
            f"/api/v1/rule-assignments/{a['id']}/accept",
            headers=auth(tokens[1]),
            json={"expected_version": a["revision"], "rule_version_id": rule["version_id"]},
        )
    ).status_code == 200
    result = await c.post(path, headers=auth(tokens[0]), json=command)
    assert result.status_code == 200, result.text
    snapshot = result.json()["versions"][0]
    assert snapshot["rule_version_id"] == rule["version_id"] and snapshot["intensity"] == 4
    assert snapshot["assignment_comment"] == "Rule comment"
