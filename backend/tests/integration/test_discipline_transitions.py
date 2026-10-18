"""Execution without acceptance, immutable links and actor boundaries."""

import asyncio
from uuid import uuid4

import pytest
from sqlalchemy import text
from test_relations import accept, members
from test_sessions import auth


async def setup(api):
    client, app = api
    ids, tokens = await members(client, app, 4)
    from vowen.modules.references.fixtures import seed_references

    async with app.state.sessions() as db, db.begin():
        await seed_references(db)
    relations = []
    for actor in (0, 2):
        r = (
            await client.post(
                "/api/v1/relations",
                headers=auth(tokens[actor]),
                json={
                    "dominant_user_id": str(ids[actor]),
                    "submissive_user_id": str(ids[1]),
                    "scopes": ["rules.assign", "discipline.propose", "discipline.review"],
                    "agreement_text": "Synthetic agreement",
                },
            )
        ).json()
        r = (await accept(client, tokens[actor], r)).json()
        r = (await accept(client, tokens[1], r)).json()
        relations.append(r)
    body = {
        "recipient_id": str(ids[1]),
        "reviewer_ids": [str(ids[0]), str(ids[2])],
        "description": "private-allegation",
        "conditions": "Voluntary reflection",
        "idempotency_key": str(uuid4()),
    }
    response = await client.post("/api/v1/discipline-records", headers=auth(tokens[0]), json=body)
    assert response.status_code == 200
    return client, app, ids, tokens, relations, response.json(), body


async def act(client, token, record, action):
    return await client.post(
        f"/api/v1/discipline-records/{record['id']}/transitions",
        headers=auth(token),
        json={
            "expected_version": record["revision"],
            "version_id": record["version_id"],
            "action": action,
            "comment": "private-comment",
        },
    )


async def test_direct_execution_history_and_concurrent_review(api):
    client, app, ids, tokens, _, r, body = await setup(api)
    assert (await act(client, tokens[0], r, "start")).status_code == 403
    for action in ("start", "complete"):
        r = (await act(client, tokens[1], r, action)).json()
    outcomes = await asyncio.gather(*(act(client, tokens[i], r, "confirm") for i in (0, 2)))
    assert sorted(x.status_code for x in outcomes) == [200, 409]
    r = next(x.json() for x in outcomes if x.status_code == 200)
    assert r["status"] == "confirmed"
    assert [h["status"] for h in r["history"]] == [
        "planned",
        "in_progress",
        "completed",
        "confirmed",
    ]
    assert r["history"][1]["actor_id"] == str(ids[1])
    assert (await client.get("/api/v1/discipline-records", headers=auth(tokens[3]))).json() == []
    assert (
        await client.get(f"/api/v1/discipline-records/{r['id']}", headers=auth(tokens[3]))
    ).status_code == 404
    replay = await client.post("/api/v1/discipline-records", headers=auth(tokens[0]), json=body)
    assert replay.json()["id"] == r["id"]
    async with app.state.engine.connect() as conn:
        for table in ("discipline_versions", "discipline_transitions"):
            values = (await conn.execute(text(f"SELECT ciphertext FROM {table}"))).scalars().all()
            assert any(b"private-" in bytes(v) for v in values)
            assert (
                await conn.scalar(
                    text(f"SELECT count(*) FROM {table} WHERE key_id != 'plaintext-v1'")
                )
                == 0
            )


@pytest.mark.parametrize("action", ["complete", "confirm"])
async def test_cannot_skip_execution_states(api, action):
    client, _, _, tokens, _, r, _ = await setup(api)
    assert (
        await act(client, tokens[1 if action != "confirm" else 0], r, action)
    ).status_code == 409


async def test_versions_reschedule_without_acceptance_and_keep_history(api):
    client, _, ids, tokens, _, r, _ = await setup(api)
    r = (await act(client, tokens[1], r, "start")).json()
    old = r["version_id"]
    body = {
        "expected_version": r["revision"],
        "description": "Changed allegation",
        "conditions": "Changed terms",
    }
    newer = await client.post(
        f"/api/v1/discipline-records/{r['id']}/versions", headers=auth(tokens[0]), json=body
    )
    assert newer.status_code == 200
    n = newer.json()
    assert n["status"] == "planned" and n["version_id"] != old
    assert (await act(client, tokens[1], r, "start")).status_code == 409
    assert (await act(client, tokens[1], n, "start")).status_code == 200
    assert n["versions"][0]["conditions"] == "Voluntary reflection"
    assert n["history"][1]["version_id"] == old
    for field, value in [
        ("recipient_id", str(ids[3])),
        ("reviewer_ids", []),
        ("author_id", str(ids[2])),
    ]:
        assert (
            await client.post(
                f"/api/v1/discipline-records/{n['id']}/versions",
                headers=auth(tokens[0]),
                json={**body, field: value},
            )
        ).status_code == 422


async def test_revoked_relation_blocks_execution_but_preserves_recipient_history(api):
    client, _, _, tokens, relations, r, _ = await setup(api)
    r = (await act(client, tokens[1], r, "start")).json()
    await client.post(
        f"/api/v1/relations/{relations[0]['id']}/revoke",
        headers=auth(tokens[1]),
        json={"expected_version": relations[0]["version"]},
    )
    assert (await client.get("/api/v1/discipline-records", headers=auth(tokens[0]))).json() == []
    assert (
        await client.get(f"/api/v1/discipline-records/{r['id']}", headers=auth(tokens[0]))
    ).status_code == 404
    # Relationship controls remain separate; recipient retains historical read access.
    await client.post("/api/v1/me/pause", headers=auth(tokens[1]))
    assert (await act(client, tokens[1], r, "complete")).status_code == 403
    assert (
        await client.get(f"/api/v1/discipline-records/{r['id']}", headers=auth(tokens[1]))
    ).status_code == 200


async def test_rule_link_is_exact_and_never_implies_violation_confirmation(api):
    client, _, ids, tokens, _, r, body = await setup(api)
    rule = (
        await client.post(
            "/api/v1/rules",
            headers=auth(tokens[0]),
            json={"title": "Rule", "description": "Original rule"},
        )
    ).json()
    rule = (
        await client.post(
            f"/api/v1/rules/{rule['id']}/publish",
            headers=auth(tokens[0]),
            json={"expected_version": rule["revision"]},
        )
    ).json()
    body = {**body, "idempotency_key": str(uuid4()), "rule_version_id": rule["version_id"]}
    assert (
        await client.post("/api/v1/discipline-records", headers=auth(tokens[0]), json=body)
    ).status_code == 403
    a = (
        await client.post(
            f"/api/v1/rules/{rule['id']}/assignments",
            headers=auth(tokens[0]),
            json={
                "rule_version_id": rule["version_id"],
                "recipient_id": str(ids[1]),
                "manager_ids": [str(ids[0])],
            },
        )
    ).json()
    await client.post(
        f"/api/v1/rule-assignments/{a['id']}/accept",
        headers=auth(tokens[1]),
        json={"expected_version": a["revision"], "rule_version_id": a["rule_version_id"]},
    )
    linked = (
        await client.post("/api/v1/discipline-records", headers=auth(tokens[0]), json=body)
    ).json()
    assert (
        linked["status"] == "planned"
        and linked["versions"][0]["rule_version_id"] == rule["version_id"]
    )
    assert linked["versions"][0]["rule_title"] == "Rule"
    assert (await act(client, tokens[0], linked, "complete")).status_code == 403


async def test_explicit_reviewers_and_active_proposer_required(api):
    client, _, ids, tokens, _, r, body = await setup(api)
    for changed in (
        {"recipient_id": str(ids[3])},
        {"reviewer_ids": [str(ids[3])]},
        {"reviewer_ids": [str(ids[1])]},
    ):
        response = await client.post(
            "/api/v1/discipline-records",
            headers=auth(tokens[0]),
            json={**body, **changed, "idempotency_key": str(uuid4())},
        )
        assert response.status_code in (403, 422)
    await client.post("/api/v1/me/pause", headers=auth(tokens[1]))
    assert (await act(client, tokens[1], r, "start")).status_code == 403
    assert (await act(client, tokens[1], r, "cancel")).status_code == 403


async def test_recipient_and_reviewer_cannot_rewrite_conditions(api):
    client, _, _, tokens, _, r, _ = await setup(api)
    for actor in (1, 2):
        response = await client.post(
            f"/api/v1/discipline-records/{r['id']}/versions",
            headers=auth(tokens[actor]),
            json={
                "expected_version": r["revision"],
                "description": "Replacement",
                "conditions": "Unauthorized",
            },
        )
        assert response.status_code == 403
    for action in ("start", "complete"):
        assert (await act(client, tokens[2], r, action)).status_code == 403
    assert (await act(client, tokens[1], r, "confirm")).status_code == 403


async def test_revoked_reviewer_cannot_confirm_or_read_history(api):
    client, _, _, tokens, relations, r, _ = await setup(api)
    for action in ("start", "complete"):
        r = (await act(client, tokens[1], r, action)).json()
    assert (
        await client.post(
            f"/api/v1/relations/{relations[1]['id']}/revoke",
            headers=auth(tokens[1]),
            json={"expected_version": relations[1]["version"]},
        )
    ).status_code == 200
    assert (await act(client, tokens[2], r, "confirm")).status_code == 404
    assert (await client.get("/api/v1/discipline-records", headers=auth(tokens[2]))).json() == []
    assert (await act(client, tokens[0], r, "confirm")).json()["status"] == "confirmed"


async def test_concurrent_create_replays_one_record_and_rejects_changed_request(api):
    client, app, _, tokens, _, r, body = await setup(api)
    results = await asyncio.gather(
        *(
            client.post("/api/v1/discipline-records", headers=auth(tokens[0]), json=body)
            for _ in range(2)
        )
    )
    assert all(x.status_code == 200 and x.json()["id"] == r["id"] for x in results)
    assert (
        await client.post(
            "/api/v1/discipline-records",
            headers=auth(tokens[0]),
            json={**body, "conditions": "Changed"},
        )
    ).status_code == 409
    async with app.state.engine.connect() as conn:
        assert (
            await conn.execute(text("SELECT count(*) FROM discipline_records"))
        ).scalar_one() == 1


async def test_authority_lock_refreshes_previously_loaded_member_after_pause(api):
    from vowen.modules.discipline.service import lock_authority, permitted
    from vowen.modules.identity.models import User

    client, app, ids, tokens, _, _, _ = await setup(api)
    async with app.state.sessions() as db, db.begin():
        cached = await db.get(User, ids[0])
        assert cached.paused is False
        assert (await client.post("/api/v1/me/pause", headers=auth(tokens[0]))).status_code == 204
        await lock_authority(db, ids[1], [ids[0]])
        assert await permitted(db, ids[0], ids[1], "discipline.propose") is False


@pytest.mark.parametrize(
    ("source", "recipient_actions", "reviewer_actions"),
    [
        ("planned", {"start"}, {"cancel"}),
        ("proposed", {"start"}, {"cancel"}),
        ("accepted", {"start"}, {"cancel"}),
        ("in_progress", {"complete"}, {"cancel"}),
        ("completed", set(), {"confirm", "cancel"}),
        ("disputed", set(), {"cancel"}),
        ("confirmed", set(), set()),
        ("declined", set(), set()),
        ("cancelled", set(), set()),
    ],
)
async def test_every_status_action_actor_boundary(api, source, recipient_actions, reviewer_actions):
    client, app, _, tokens, _, r, _ = await setup(api)
    path = f"/api/v1/discipline-records/{r['id']}"
    for actor in (0, 1, 2, 3):
        for action in ("start", "complete", "confirm", "cancel"):
            async with app.state.engine.begin() as conn:
                await conn.execute(
                    text("DELETE FROM discipline_transitions WHERE record_id=:id AND revision>1"),
                    {"id": r["id"]},
                )
                await conn.execute(
                    text("UPDATE discipline_records SET status=:status,revision=1 WHERE id=:id"),
                    {"id": r["id"], "status": source},
                )
            allowed = (
                recipient_actions
                if actor == 1
                else reviewer_actions
                if actor == 0
                else reviewer_actions - {"cancel"}
                if actor == 2
                else set()
            )
            response = await act(client, tokens[actor], r, action)
            if action in allowed:
                assert response.status_code == 200, (source, actor, action, response.text)
            else:
                assert response.status_code in (403, 404, 409), (
                    source,
                    actor,
                    action,
                    response.text,
                )
                latest = (await client.get(path, headers=auth(tokens[1]))).json()
                assert latest["status"] == source and latest["revision"] == 1


@pytest.mark.parametrize("action", ["accept", "decline", "dispute"])
async def test_acceptance_actions_are_no_longer_part_of_api(api, action):
    client, _, _, tokens, _, r, _ = await setup(api)
    assert (await act(client, tokens[1], r, action)).status_code == 422
