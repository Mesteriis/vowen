import asyncio
from uuid import uuid4

from test_ritual_review import setup_ritual
from test_rule_acceptance import action, assign, setup_rule
from test_sessions import auth


async def decision(client, token, row, outcome="approve"):
    return await client.post(
        f"/api/v1/change-requests/{row['id']}/{outcome}",
        headers=auth(token),
        json={"expected_version": row["revision"], "comment": "Decision"},
    )


async def test_skip_is_request_only_issuer_decides_once(api):
    client, app, ids, tokens, template, a, o = await setup_ritual(api)
    command = {
        "kind": "ritual_skip",
        "assignment_id": a["id"],
        "occurrence_id": o["id"],
        "expected_version": o["revision"],
        "idempotency_key": str(uuid4()),
        "reason": "Private synthetic reason",
    }
    assert (
        await client.post(
            f"/api/v1/ritual-occurrences/{o['id']}/skip",
            headers=auth(tokens[1]),
            json={"expected_version": o["revision"]},
        )
    ).status_code == 403
    responses = await asyncio.gather(
        *(
            client.post("/api/v1/change-requests", headers=auth(tokens[1]), json=command)
            for _ in range(2)
        )
    )
    assert [r.status_code for r in responses] == [200, 200]
    row = responses[0].json()
    assert row == responses[1].json() and row["status"] == "pending"
    assert (await decision(client, tokens[1], row)).status_code == 404
    assert (await decision(client, tokens[2], row)).status_code == 404  # reviewer != issuer
    assert (await client.get("/api/v1/change-requests", headers=auth(tokens[3]))).json() == []
    current = (await client.get("/api/v1/ritual-occurrences", headers=auth(tokens[1]))).json()
    assert next(x for x in current if x["id"] == o["id"])["status"] == "scheduled"
    decisions = await asyncio.gather(*(decision(client, tokens[0], row) for _ in range(2)))
    assert [r.status_code for r in decisions] == [200, 200]
    current = (await client.get("/api/v1/ritual-occurrences", headers=auth(tokens[1]))).json()
    assert next(x for x in current if x["id"] == o["id"])["status"] == "skipped"
    assert (await decision(client, tokens[0], row, "reject")).status_code == 409
    assert (
        await client.post(
            "/api/v1/change-requests",
            headers=auth(tokens[1]),
            json={**command, "reason": "Changed"},
        )
    ).status_code == 409


async def test_pause_rejection_withdrawal_and_stale_target(api):
    client, app, ids, tokens, template, a, o = await setup_ritual(api)
    command = {
        "kind": "ritual_pause",
        "assignment_id": a["id"],
        "expected_version": a["revision"],
        "idempotency_key": str(uuid4()),
        "reason": "Rest",
    }
    assert (
        await client.post(
            f"/api/v1/ritual-assignments/{a['id']}/pause",
            headers=auth(tokens[1]),
            json={"expected_version": a["revision"]},
        )
    ).status_code == 403
    row = (
        await client.post("/api/v1/change-requests", headers=auth(tokens[1]), json=command)
    ).json()
    assert (await decision(client, tokens[0], row, "reject")).json()["status"] == "rejected"
    row = (
        await client.post(
            "/api/v1/change-requests",
            headers=auth(tokens[1]),
            json={**command, "idempotency_key": str(uuid4())},
        )
    ).json()
    assert (await decision(client, tokens[1], row, "withdraw")).json()["status"] == "withdrawn"
    row = (
        await client.post(
            "/api/v1/change-requests",
            headers=auth(tokens[1]),
            json={**command, "idempotency_key": str(uuid4())},
        )
    ).json()
    assert (await decision(client, tokens[0], row)).json()["status"] == "approved"
    assignments = (await client.get("/api/v1/ritual-assignments", headers=auth(tokens[1]))).json()
    paused = next(x for x in assignments if x["id"] == a["id"])
    assert paused["status"] == "paused"
    assert (
        await client.post(
            f"/api/v1/ritual-assignments/{a['id']}/resume",
            headers=auth(tokens[0]),
            json={"expected_version": paused["revision"]},
        )
    ).json()["status"] == "active"


async def test_rules_add_edit_delete_are_versioned_proposals(api):
    client, app, ids, tokens, rule = await setup_rule(api)
    a = (await assign(client, tokens[0], rule, ids[1], [ids[0]])).json()
    a = (await action(client, tokens[1], a, "accept")).json()
    relations = (await client.get("/api/v1/relations", headers=auth(tokens[1]))).json()
    relation = next(r for r in relations if r["submissive_user_id"] == str(ids[1]))
    base = {
        "relation_id": relation["id"],
        "idempotency_key": str(uuid4()),
        "reason": "Reason",
        "content": {"title": "Proposed", "description": "Private proposal", "discipline": "Agreed"},
    }
    edit = {
        **base,
        "kind": "rule_edit",
        "assignment_id": a["id"],
        "expected_version": a["revision"],
    }
    row = (await client.post("/api/v1/change-requests", headers=auth(tokens[1]), json=edit)).json()
    assert (await decision(client, tokens[0], row)).json()["status"] == "approved"
    assignments = (await client.get("/api/v1/rule-assignments", headers=auth(tokens[1]))).json()
    assert next(x for x in assignments if x["id"] == a["id"])["status"] == "active"
    replacement = next(x for x in assignments if x["id"] != a["id"])
    assert replacement["title"] == "Proposed" and replacement["status"] == "pending_acceptance"
    replacement = (await action(client, tokens[1], replacement, "accept")).json()
    delete = {
        **base,
        "content": None,
        "idempotency_key": str(uuid4()),
        "kind": "rule_delete",
        "assignment_id": replacement["id"],
        "expected_version": replacement["revision"],
    }
    row = (
        await client.post("/api/v1/change-requests", headers=auth(tokens[1]), json=delete)
    ).json()
    assert (await decision(client, tokens[0], row)).json()["status"] == "approved"
    add = {**base, "idempotency_key": str(uuid4()), "kind": "rule_add"}
    row = (await client.post("/api/v1/change-requests", headers=auth(tokens[1]), json=add)).json()
    assert (await decision(client, tokens[0], row)).json()["status"] == "approved"
    assert (
        await client.post("/api/v1/change-requests", headers=auth(tokens[2]), json=add)
    ).status_code == 404


async def test_revoked_authority_hides_requests_but_preserves_requester_history(api):
    from sqlalchemy import text

    client, app, ids, tokens, template, a, o = await setup_ritual(api)
    command = {
        "kind": "ritual_skip",
        "assignment_id": a["id"],
        "occurrence_id": o["id"],
        "expected_version": o["revision"],
        "idempotency_key": str(uuid4()),
        "reason": "Plain storage with requester-only history",
    }
    row = (
        await client.post("/api/v1/change-requests", headers=auth(tokens[1]), json=command)
    ).json()
    async with app.state.sessions() as db:
        stored = (await db.execute(text("SELECT ciphertext FROM change_requests"))).scalar_one()
        assert command["reason"].encode() in stored
    relation = next(
        r
        for r in (await client.get("/api/v1/relations", headers=auth(tokens[0]))).json()
        if r["dominant_user_id"] == str(ids[0])
    )
    assert (
        await client.post(
            f"/api/v1/relations/{relation['id']}/revoke",
            headers=auth(tokens[0]),
            json={"expected_version": relation["version"]},
        )
    ).status_code == 200
    assert (await client.get("/api/v1/change-requests", headers=auth(tokens[0]))).json() == []
    assert (await decision(client, tokens[0], row)).status_code == 403
    own = (await client.get("/api/v1/change-requests", headers=auth(tokens[1]))).json()
    assert own[0]["reason"] == command["reason"]
    assert (await decision(client, tokens[1], row, "withdraw")).json()["status"] == "withdrawn"


async def test_stale_occurrence_and_personal_pause_cannot_be_approved(api):
    client, app, ids, tokens, template, a, o = await setup_ritual(api)
    command = {
        "kind": "ritual_skip",
        "assignment_id": a["id"],
        "occurrence_id": o["id"],
        "expected_version": o["revision"],
        "idempotency_key": str(uuid4()),
        "reason": "Conflict",
    }
    row = (
        await client.post("/api/v1/change-requests", headers=auth(tokens[1]), json=command)
    ).json()
    assert (await client.post("/api/v1/me/pause", headers=auth(tokens[1]))).status_code == 204
    assert (await decision(client, tokens[0], row)).status_code == 403
    assert (await client.post("/api/v1/me/resume", headers=auth(tokens[1]))).status_code == 204
    assert (await decision(client, tokens[0], row)).status_code == 409
    assert (await decision(client, tokens[0], row, "reject")).json()["status"] == "rejected"


async def test_rule_edit_stale_version_does_not_overwrite_dominant_draft(api):
    client, app, ids, tokens, rule = await setup_rule(api)
    a = (await assign(client, tokens[0], rule, ids[1], [ids[0]])).json()
    a = (await action(client, tokens[1], a, "accept")).json()
    command = {
        "kind": "rule_edit",
        "assignment_id": a["id"],
        "expected_version": a["revision"],
        "idempotency_key": str(uuid4()),
        "reason": "Edit",
        "content": {"title": "Suggestion", "description": "Proposed changes"},
    }
    row = (
        await client.post("/api/v1/change-requests", headers=auth(tokens[1]), json=command)
    ).json()
    assert (
        await client.post(
            f"/api/v1/rules/{rule['id']}/versions",
            headers=auth(tokens[0]),
            json={
                "expected_version": rule["revision"],
                "title": "Dominant draft",
                "description": "Saved draft",
            },
        )
    ).status_code == 200
    assert (await decision(client, tokens[0], row)).status_code == 409
    templates = (await client.get("/api/v1/rules", headers=auth(tokens[0]))).json()
    assert templates[0]["title"] == "Dominant draft"
    assert (await decision(client, tokens[1], row, "withdraw")).status_code == 200


async def test_changed_agreement_and_expired_slot_require_new_request(api):
    from test_relations import accept

    client, app, ids, tokens, template, a, o = await setup_ritual(api)
    command = {
        "kind": "ritual_skip",
        "assignment_id": a["id"],
        "occurrence_id": o["id"],
        "expected_version": o["revision"],
        "idempotency_key": str(uuid4()),
        "reason": "Later",
    }
    row = (
        await client.post("/api/v1/change-requests", headers=auth(tokens[1]), json=command)
    ).json()
    assert (
        await client.post(
            "/api/v1/change-requests",
            headers=auth(tokens[1]),
            json={**command, "idempotency_key": str(uuid4())},
        )
    ).status_code == 409
    r = next(
        r
        for r in (await client.get("/api/v1/relations", headers=auth(tokens[0]))).json()
        if r["dominant_user_id"] == str(ids[0])
    )
    changed = await client.post(
        f"/api/v1/relations/{r['id']}/versions",
        headers=auth(tokens[0]),
        json={
            "expected_version": r["version"],
            "scopes": r["scopes"],
            "agreement_text": "New agreement",
        },
    )
    assert changed.status_code == 200
    r = (await accept(client, tokens[0], changed.json())).json()
    assert (await accept(client, tokens[1], r)).status_code == 200
    assert (await decision(client, tokens[0], row)).status_code == 409
    assert (await decision(client, tokens[1], row, "withdraw")).status_code == 200


async def test_expired_slot_is_rechecked_without_waiting_for_worker(api):
    from datetime import timedelta

    from conftest import NOW
    from sqlalchemy import text

    client, app, ids, tokens, template, a, o = await setup_ritual(api)
    command = {
        "kind": "ritual_skip",
        "assignment_id": a["id"],
        "occurrence_id": o["id"],
        "expected_version": o["revision"],
        "idempotency_key": str(uuid4()),
        "reason": "Later",
    }
    row = (
        await client.post("/api/v1/change-requests", headers=auth(tokens[1]), json=command)
    ).json()
    async with app.state.sessions() as db, db.begin():
        await db.execute(
            text("UPDATE ritual_occurrences SET expires_at=:at WHERE id=:id"),
            {"at": NOW - timedelta(seconds=1), "id": o["id"]},
        )
    assert (await decision(client, tokens[0], row)).status_code == 409
