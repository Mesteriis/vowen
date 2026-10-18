import asyncio
from uuid import uuid4

from sqlalchemy import text
from test_discipline_transitions import act, setup
from test_sessions import auth


async def test_relation_dictionaries_isolation_repeat_and_physical_snapshot(api):
    c, app, ids, tokens, relations, original, base = await setup(api)
    path = f"/api/v1/discipline-records/dictionaries/{relations[0]['id']}/device"
    assert "Рука" in (await c.get(path, headers=auth(tokens[0]))).json()
    for actor, status in ((1, 403), (2, 404), (3, 404)):
        response = await c.post(path, headers=auth(tokens[actor]), json={"name": "Synthetic tool"})
        assert response.status_code == status
    results = await asyncio.gather(
        *(
            c.post(path, headers=auth(tokens[0]), json={"name": "  Synthetic tool  "})
            for _ in range(2)
        )
    )
    assert all(r.status_code == 200 for r in results)
    values = (await c.get(path, headers=auth(tokens[1]))).json()
    assert values.count("Synthetic tool") == 1
    other = f"/api/v1/discipline-records/dictionaries/{relations[1]['id']}/device"
    assert "Synthetic tool" not in (await c.get(other, headers=auth(tokens[2]))).json()
    assert (await c.get(path, headers=auth(tokens[2]))).status_code == 404
    physical = {
        **base,
        "idempotency_key": str(uuid4()),
        "punishment_type": "physical",
        "device": "Synthetic tool",
        "body_part": "Руки",
        "strike_count": 1,
        "intensity": 1,
    }
    created = await c.post("/api/v1/discipline-records", headers=auth(tokens[0]), json=physical)
    assert created.status_code == 200, created.text
    record = created.json()
    assert record["versions"][0]["strike_count"] == 1
    record = (await act(c, tokens[1], record, "start")).json()
    edit = {
        k: v
        for k, v in physical.items()
        if k not in ("recipient_id", "reviewer_ids", "idempotency_key")
    }
    edit.update(expected_version=record["revision"], intensity=2)
    endpoint = f"/api/v1/discipline-records/{record['id']}/versions"
    assert (await c.post(endpoint, headers=auth(tokens[1]), json=edit)).status_code == 403
    changed = (await c.post(endpoint, headers=auth(tokens[0]), json=edit)).json()
    assert changed["status"] == "planned"
    assert [v["intensity"] for v in changed["versions"]] == [1, 2]
    assert (await c.post(endpoint, headers=auth(tokens[0]), json=edit)).status_code == 409
    invalid = {**physical, "device": "Unknown tool", "idempotency_key": str(uuid4())}
    assert (
        await c.post("/api/v1/discipline-records", headers=auth(tokens[0]), json=invalid)
    ).status_code == 422
    async with app.state.engine.connect() as conn:
        encrypted = (
            (await conn.execute(text("SELECT ciphertext FROM discipline_dictionary")))
            .scalars()
            .all()
        )
        assert all(b"Synthetic tool" in bytes(value) for value in encrypted)
    # Legacy records remain readable with default type.
    assert original["versions"][0]["punishment_type"] == "other"


async def test_ban_duration_and_paused_dictionary(api):
    c, _, _, tokens, relations, _, base = await setup(api)
    body = {**base, "idempotency_key": str(uuid4()), "punishment_type": "ban", "ban_days": 3}
    created = await c.post("/api/v1/discipline-records", headers=auth(tokens[0]), json=body)
    assert created.status_code == 200
    assert created.json()["versions"][0]["ban_days"] == 3
    assert (
        await c.post(
            "/api/v1/discipline-records",
            headers=auth(tokens[1]),
            json={
                **body,
                "recipient_id": base["reviewer_ids"][0],
                "reviewer_ids": [base["recipient_id"]],
            },
        )
    ).status_code == 403
    assert (
        await c.post(
            "/api/v1/discipline-records",
            headers=auth(tokens[0]),
            json={**body, "idempotency_key": str(uuid4()), "ban_days": 0},
        )
    ).status_code == 422

    paused = await c.post(
        f"/api/v1/relations/{relations[0]['id']}/pause",
        headers=auth(tokens[1]),
        json={"expected_version": relations[0]["version"]},
    )
    assert paused.status_code == 200
    path = f"/api/v1/discipline-records/dictionaries/{relations[0]['id']}/device"
    assert (
        await c.post(path, headers=auth(tokens[0]), json={"name": "After pause"})
    ).status_code == 403
