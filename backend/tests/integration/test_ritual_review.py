import asyncio
from datetime import timedelta
from uuid import uuid4

from conftest import NOW
from sqlalchemy import text
from test_relations import accept, members
from test_sessions import auth, login
from test_telegram_validation import signed


async def setup_ritual(api, approval=True):
    client, app = api
    ids, tokens = await members(client, app, 4)
    for actor in (0, 2):
        relation = (
            await client.post(
                "/api/v1/relations",
                headers=auth(tokens[actor]),
                json={
                    "dominant_user_id": str(ids[actor]),
                    "submissive_user_id": str(ids[1]),
                    "scopes": ["rituals.assign", "rituals.review"],
                    "agreement_text": "Synthetic ritual authority",
                },
            )
        ).json()
        relation = (await accept(client, tokens[actor], relation)).json()
        assert (await accept(client, tokens[1], relation)).status_code == 200
    created = await client.post(
        "/api/v1/rituals",
        headers=auth(tokens[0]),
        json={"title": "Morning presence", "description": "Private synthetic ritual"},
    )
    assert created.status_code == 200
    template = created.json()
    template = (
        await client.post(
            f"/api/v1/rituals/{template['id']}/publish",
            headers=auth(tokens[0]),
            json={"expected_version": template["revision"]},
        )
    ).json()
    command = {
        "recipient_id": str(ids[1]),
        "reviewer_ids": [str(ids[0]), str(ids[2])],
        "approval_required": approval,
        "idempotency_key": str(uuid4()),
        "schedule": {
            "kind": "daily",
            "timezone": "UTC",
            "hour": 9,
            "minute": 0,
            "start_date": "2026-10-15",
            "window_hours": 24,
        },
    }
    response = await client.post(
        f"/api/v1/rituals/{template['id']}/assignments", headers=auth(tokens[0]), json=command
    )
    assert response.status_code == 200
    assignment = response.json()
    assert (
        await client.post(
            f"/api/v1/rituals/{template['id']}/assignments", headers=auth(tokens[0]), json=command
        )
    ).json()["id"] == assignment["id"]
    occurrence = (await client.get("/api/v1/ritual-occurrences", headers=auth(tokens[1]))).json()[0]
    return client, app, ids, tokens, template, assignment, occurrence


async def test_report_attempts_idempotency_and_conflicting_reviewers(api):
    client, app, ids, tokens, template, assignment, o = await setup_ritual(api)
    path = f"/api/v1/ritual-occurrences/{o['id']}"
    report = {
        "expected_version": o["revision"],
        "idempotency_key": str(uuid4()),
        "text": "Private first attempt",
    }
    assert (
        await client.post(path + "/report", headers=auth(tokens[0]), json=report)
    ).status_code == 403
    sent = await asyncio.gather(
        *(client.post(path + "/report", headers=auth(tokens[1]), json=report) for _ in range(2))
    )
    assert [r.status_code for r in sent] == [200, 200]
    o = sent[0].json()
    assert o["status"] == "submitted" and len(o["reports"]) == 1
    review = {"expected_version": o["revision"], "comment": "Private feedback"}
    outcomes = await asyncio.gather(
        *(
            client.post(
                path + "/review", headers=auth(tokens[actor]), json={**review, "decision": decision}
            )
            for actor, decision in [(0, "needs_changes"), (2, "approved")]
        )
    )
    assert sorted(r.status_code for r in outcomes) == [200, 409]
    final = next(r.json() for r in outcomes if r.status_code == 200)
    assert final["reports"][0]["comment"] == "Private feedback"
    if final["status"] == "needs_changes":
        second = await client.post(
            path + "/report",
            headers=auth(tokens[1]),
            json={
                "expected_version": final["revision"],
                "idempotency_key": str(uuid4()),
                "text": "Private revised attempt",
            },
        )
        assert second.status_code == 200 and len(second.json()["reports"]) == 2
    assert (await client.get("/api/v1/ritual-occurrences", headers=auth(tokens[3]))).json() == []
    assert (await client.get("/api/v1/ritual-assignments", headers=auth(tokens[3]))).json() == []
    async with app.state.engine.connect() as conn:
        payloads = (
            (await conn.execute(text("SELECT ciphertext FROM ritual_reports"))).scalars().all()
        )
        assert payloads and all(b"Private" not in bytes(p) for p in payloads)


async def test_needs_changes_history_autoapproval_and_pause(api):
    client, app, ids, tokens, template, a, o = await setup_ritual(api)
    path = f"/api/v1/ritual-occurrences/{o['id']}"
    o = (
        await client.post(
            path + "/report",
            headers=auth(tokens[1]),
            json={
                "expected_version": o["revision"],
                "idempotency_key": str(uuid4()),
                "text": "First",
            },
        )
    ).json()
    o = (
        await client.post(
            path + "/review",
            headers=auth(tokens[0]),
            json={
                "expected_version": o["revision"],
                "decision": "needs_changes",
                "comment": "Try again",
            },
        )
    ).json()
    o = (
        await client.post(
            path + "/report",
            headers=auth(tokens[1]),
            json={
                "expected_version": o["revision"],
                "idempotency_key": str(uuid4()),
                "text": "Second",
            },
        )
    ).json()
    assert [r["text"] for r in o["reports"]] == ["First", "Second"]
    assert o["reports"][0]["decision"] == "needs_changes"
    assert [r["attempt"] for r in o["reports"]] == [1, 2]
    await client.post("/api/v1/me/pause", headers=auth(tokens[1]))
    assert (
        await client.post(
            path + "/review",
            headers=auth(tokens[0]),
            json={"expected_version": o["revision"], "decision": "approved"},
        )
    ).status_code in (403, 404)
    assert (await client.get("/api/v1/ritual-occurrences", headers=auth(tokens[0]))).json() == []
    assert (
        len((await client.get("/api/v1/ritual-occurrences", headers=auth(tokens[1]))).json()) == 1
    )
    assert (
        await client.post(
            f"/api/v1/ritual-assignments/{a['id']}/pause",
            headers=auth(tokens[1]),
            json={"expected_version": a["revision"]},
        )
    ).status_code == 200


async def test_worker_bounded_catchup_unique_slots_and_schedule_revision(api):
    from vowen.modules.rituals.worker import generate

    client, app, ids, tokens, template, a, o = await setup_ritual(api, False)
    later = NOW + timedelta(days=5)

    async def tick():
        async with app.state.sessions() as db, db.begin():
            await generate(db, later, days_limit=2)

    await asyncio.gather(tick(), tick())
    for _ in range(4):
        await tick()
    rows = (await client.get("/api/v1/ritual-occurrences", headers=auth(tokens[1]))).json()
    assert len(rows) == 6 and len({r["local_day"] for r in rows}) == 6
    assert sum(r["status"] == "missed" for r in rows) == 5
    # Deterministic worker clock differs from request clock: report a currently due slot.
    app.state.clock = type("LaterClock", (), {"now": lambda self: later})()
    tokens = [
        (
            await login(client, signed(100000000001 + i, offset=5 * 86400, query_id=str(uuid4())))
        ).json()
        for i in range(4)
    ]
    current = next(r for r in rows if r["status"] == "scheduled")
    result = await client.post(
        f"/api/v1/ritual-occurrences/{current['id']}/report",
        headers=auth(tokens[1]),
        json={
            "expected_version": current["revision"],
            "idempotency_key": str(uuid4()),
            "text": "Done without review",
        },
    )
    assert result.json()["status"] == "approved"
    edited = await client.put(
        f"/api/v1/ritual-assignments/{a['id']}/schedule",
        headers=auth(tokens[0]),
        json={
            "expected_version": a["revision"],
            "schedule": {
                "kind": "daily",
                "timezone": "UTC",
                "hour": 14,
                "minute": 0,
                "start_date": "2026-10-21",
                "window_hours": 24,
            },
        },
    )
    assert edited.status_code == 200
    async with app.state.sessions() as db, db.begin():
        await generate(db, later + timedelta(days=1))
    rows = (await client.get("/api/v1/ritual-occurrences", headers=auth(tokens[1]))).json()
    assert (
        len(rows) == 7
        and next(r for r in rows if r["local_day"] == "2026-10-21")["due_at"]
        == "2026-10-21T14:00:00Z"
    )
    assert next(r for r in rows if r["id"] == current["id"])["due_at"] == current["due_at"]


async def test_worker_pause_cancels_obligation_without_replaying_or_leaking_notices(api):
    from vowen.modules.rituals.worker import generate

    client, app, ids, tokens, template, a, o = await setup_ritual(api)
    assert (await client.post("/api/v1/me/pause", headers=auth(tokens[1]))).status_code == 204
    async with app.state.sessions() as db, db.begin():
        await generate(db, NOW)
    rows = (await client.get("/api/v1/ritual-occurrences", headers=auth(tokens[1]))).json()
    assert rows[0]["status"] == "cancelled"
    assert (await client.get("/api/v1/ritual-notices", headers=auth(tokens[0]))).json() == []
    assert (await client.post("/api/v1/me/resume", headers=auth(tokens[1]))).status_code == 204
    async with app.state.sessions() as db, db.begin():
        await generate(db, NOW + timedelta(days=2))
    rows = (await client.get("/api/v1/ritual-occurrences", headers=auth(tokens[1]))).json()
    assert next(r for r in rows if r["id"] == o["id"])["status"] == "cancelled"
    assert len({r["local_day"] for r in rows}) == len(rows)


async def test_pause_interval_survives_worker_downtime(api):
    from vowen.modules.rituals.worker import generate

    client, app, ids, tokens, template, a, o = await setup_ritual(api)
    await client.post("/api/v1/me/pause", headers=auth(tokens[1]))
    later = NOW + timedelta(days=5)
    app.state.clock = type("LaterClock", (), {"now": lambda self: later})()
    tokens[1] = (
        await login(client, signed(100000000002, offset=5 * 86400, query_id=str(uuid4())))
    ).json()
    assert (await client.post("/api/v1/me/resume", headers=auth(tokens[1]))).status_code == 204
    async with app.state.sessions() as db, db.begin():
        await generate(db, later)
    rows = (await client.get("/api/v1/ritual-occurrences", headers=auth(tokens[1]))).json()
    assert len(rows) == 1 and rows[0]["status"] == "cancelled"
