import asyncio
from uuid import uuid4

from test_rewards import reward_setup
from test_sessions import auth


async def context(api):
    client, app, ids, tokens, ritual, reward = await reward_setup(api)
    relations = (await client.get("/api/v1/relations", headers=auth(tokens[0]))).json()
    relation = next(r for r in relations if r["submissive_user_id"] == str(ids[1]))
    return client, app, ids, tokens, ritual, reward, relation


async def test_relation_currency_manual_retry_acl_and_purchase_race(api):
    c, app, ids, t, ritual, reward, r = await context(api)
    path = f"/api/v1/relations/{r['id']}/wallet"
    body = {"amount": 30, "comment": "За старание", "idempotency_key": str(uuid4())}
    results = await asyncio.gather(
        *(c.post(path + "/credits", headers=auth(t[0]), json=body) for _ in range(2))
    )
    assert [x.status_code for x in results] == [200, 200]
    assert results[0].json()["balance"] == 30
    assert len(results[1].json()["entries"]) == 1
    assert (await c.get(path, headers=auth(t[3]))).status_code == 404
    assert (await c.post(path + "/credits", headers=auth(t[1]), json=body)).status_code == 403
    assert (
        await c.post(path + "/credits", headers=auth(t[0]), json={**body, "amount": 31})
    ).status_code == 409
    listing = await c.post(
        f"/api/v1/relations/{r['id']}/shop",
        headers=auth(t[0]),
        json={"reward_version_id": reward["version_id"], "price": 20},
    )
    assert listing.status_code == 200
    buy = f"/api/v1/shop/{listing.json()['id']}/purchases"
    assert (
        await c.post(
            buy,
            headers=auth(t[0]),
            json={"idempotency_key": str(uuid4()), "expected_version": 1},
        )
    ).status_code == 403
    results = await asyncio.gather(
        *(
            c.post(
                buy,
                headers=auth(t[1]),
                json={"idempotency_key": str(uuid4()), "expected_version": 1},
            )
            for _ in range(2)
        )
    )
    assert sorted(x.status_code for x in results) == [200, 409]
    bought = next(x.json() for x in results if x.status_code == 200)
    assert bought["status"] == "accepted"
    wallet = (await c.get(path, headers=auth(t[1]))).json()
    assert wallet["balance"] == 10 and len(wallet["entries"]) == 2
    assert next(e for e in wallet["entries"] if e["kind"] == "manual")["comment"] == "За старание"
    await c.post(
        f"/api/v1/relations/{r['id']}/revoke",
        headers=auth(t[0]),
        json={"expected_version": r["version"]},
    )
    assert (await c.get(path, headers=auth(t[1]))).json()["balance"] == 10
    assert (await c.get(f"/api/v1/relations/{r['id']}/shop", headers=auth(t[1]))).json() == []
    assert (
        await c.post(
            path + "/credits", headers=auth(t[0]), json={**body, "idempotency_key": str(uuid4())}
        )
    ).status_code == 403


async def test_bundle_awards_multiple_lots_and_currency_once_without_review(api):
    c, app, ids, t, ritual, reward, r = await context(api)
    second = (
        await c.post(
            "/api/v1/rewards",
            headers=auth(t[0]),
            json={"title": "Second", "description": "Another choice"},
        )
    ).json()
    command = {
        "idempotency_key": str(uuid4()),
        "recipient_id": str(ids[1]),
        "reviewer_ids": [],
        "approval_required": False,
        "reward_version_ids": [reward["version_id"], second["version_id"]],
        "currency_amount": 25,
        "schedule": {
            "kind": "daily",
            "timezone": "UTC",
            "hour": 9,
            "minute": 0,
            "start_date": "2026-10-15",
        },
    }
    a = await c.post(
        f"/api/v1/rituals/{ritual['id']}/assignments", headers=auth(t[0]), json=command
    )
    assert a.status_code == 200
    a = a.json()
    o = next(
        x
        for x in (await c.get("/api/v1/ritual-occurrences", headers=auth(t[1]))).json()
        if x["assignment_id"] == a["id"]
    )
    report = {"expected_version": o["revision"], "idempotency_key": str(uuid4()), "text": "Done"}
    path = f"/api/v1/ritual-occurrences/{o['id']}/report"
    outcomes = await asyncio.gather(
        *(c.post(path, headers=auth(t[1]), json=report) for _ in range(2))
    )
    assert all(x.status_code == 200 for x in outcomes)
    grants = (await c.get("/api/v1/reward-grants", headers=auth(t[1]))).json()
    assert len(grants) == 2 and all(x["status"] == "accepted" for x in grants)
    wallet = (await c.get(f"/api/v1/relations/{r['id']}/wallet", headers=auth(t[1]))).json()
    assert wallet["balance"] == 25 and len(wallet["entries"]) == 1


async def test_purchase_retry_stale_price_and_relationship_isolation(api):
    c, app, ids, t, ritual, reward, r = await context(api)
    path = f"/api/v1/relations/{r['id']}/wallet"
    await c.post(
        path + "/credits",
        headers=auth(t[0]),
        json={"amount": 50, "comment": "Initial", "idempotency_key": str(uuid4())},
    )
    listing = (
        await c.post(
            f"/api/v1/relations/{r['id']}/shop",
            headers=auth(t[0]),
            json={"reward_version_id": reward["version_id"], "price": 20},
        )
    ).json()
    buy = f"/api/v1/shop/{listing['id']}/purchases"
    command = {"expected_version": 1, "idempotency_key": str(uuid4())}
    bought = (await c.post(buy, headers=auth(t[1]), json=command)).json()
    changed = await c.patch(
        f"/api/v1/shop/{listing['id']}",
        headers=auth(t[0]),
        json={"expected_version": 1, "price": 25, "active": True},
    )
    assert changed.status_code == 200
    assert (await c.post(buy, headers=auth(t[1]), json=command)).json()["id"] == bought["id"]
    assert (
        await c.post(buy, headers=auth(t[1]), json={**command, "idempotency_key": str(uuid4())})
    ).status_code == 409
    other = next(
        x
        for x in (await c.get("/api/v1/relations", headers=auth(t[2]))).json()
        if x["dominant_user_id"] == str(ids[2])
    )
    assert (await c.get(f"/api/v1/relations/{other['id']}/wallet", headers=auth(t[1]))).json()[
        "balance"
    ] == 0
    assert (await c.get(path, headers=auth(t[1]))).json()["balance"] == 30
    assert (await c.post(buy, headers=auth(t[3]), json=command)).status_code == 404


async def test_bundle_waits_for_review_and_scope_withdrawal_prevents_awards(api):
    from test_relations import accept

    c, app, ids, t, ritual, reward, r = await context(api)
    command = {
        "idempotency_key": str(uuid4()),
        "recipient_id": str(ids[1]),
        "reviewer_ids": [str(ids[0])],
        "reward_version_ids": [reward["version_id"]],
        "currency_amount": 10,
        "schedule": {
            "kind": "daily",
            "timezone": "UTC",
            "hour": 9,
            "minute": 0,
            "start_date": "2026-10-15",
        },
    }
    a = (
        await c.post(
            f"/api/v1/rituals/{ritual['id']}/assignments", headers=auth(t[0]), json=command
        )
    ).json()
    o = next(
        x
        for x in (await c.get("/api/v1/ritual-occurrences", headers=auth(t[1]))).json()
        if x["assignment_id"] == a["id"]
    )
    path = f"/api/v1/ritual-occurrences/{o['id']}"
    o = (
        await c.post(
            path + "/report",
            headers=auth(t[1]),
            json={
                "expected_version": o["revision"],
                "idempotency_key": str(uuid4()),
                "text": "Done",
            },
        )
    ).json()
    wallet = f"/api/v1/relations/{r['id']}/wallet"
    assert (await c.get(wallet, headers=auth(t[1]))).json()["balance"] == 0
    o = (
        await c.post(
            path + "/review",
            headers=auth(t[0]),
            json={"expected_version": o["revision"], "decision": "needs_changes"},
        )
    ).json()
    assert (await c.get(wallet, headers=auth(t[1]))).json()["balance"] == 0
    o = (
        await c.post(
            path + "/report",
            headers=auth(t[1]),
            json={
                "expected_version": o["revision"],
                "idempotency_key": str(uuid4()),
                "text": "Revised",
            },
        )
    ).json()
    r = (
        await c.post(
            f"/api/v1/relations/{r['id']}/versions",
            headers=auth(t[0]),
            json={
                "expected_version": r["version"],
                "agreement_text": "No rewards",
                "scopes": ["rituals.assign", "rituals.review"],
            },
        )
    ).json()
    r = (await accept(c, t[0], r)).json()
    assert (await accept(c, t[1], r)).status_code == 200
    assert (
        await c.post(
            path + "/review",
            headers=auth(t[0]),
            json={"expected_version": o["revision"], "decision": "approved"},
        )
    ).status_code == 200
    assert (await c.get(wallet, headers=auth(t[1]))).json()["balance"] == 0
    assert (await c.get("/api/v1/reward-grants", headers=auth(t[1]))).json() == []


async def test_currency_comment_encrypted_and_ledger_immutable(api):
    import pytest
    from sqlalchemy import select, update
    from sqlalchemy.exc import DBAPIError

    from vowen.modules.rewards.economy_models import CurrencyEntry

    c, app, ids, t, ritual, reward, r = await context(api)
    path = f"/api/v1/relations/{r['id']}/wallet"
    assert (
        await c.post(
            path + "/credits",
            headers=auth(t[0]),
            json={"amount": 0, "comment": "No", "idempotency_key": str(uuid4())},
        )
    ).status_code == 422
    await c.post(
        path + "/credits",
        headers=auth(t[0]),
        json={"amount": 10, "comment": "Sensitive comment", "idempotency_key": str(uuid4())},
    )
    async with app.state.sessions() as db:
        entry = await db.scalar(select(CurrencyEntry))
        assert b"Sensitive comment" not in entry.ciphertext
        with pytest.raises(DBAPIError):
            await db.execute(update(CurrencyEntry).values(amount=999))
        await db.rollback()
    assert (await c.get(path, headers=auth(t[1]))).json()["balance"] == 10


async def test_bundle_policy_changes_only_future_slots_and_confirmed_award_once(api):
    c, app, ids, t, ritual, reward, r = await context(api)
    command = {
        "idempotency_key": str(uuid4()),
        "recipient_id": str(ids[1]),
        "reviewer_ids": [str(ids[0])],
        "reward_version_ids": [reward["version_id"]],
        "currency_amount": 12,
        "schedule": {
            "kind": "daily",
            "timezone": "UTC",
            "hour": 9,
            "minute": 0,
            "start_date": "2026-10-15",
        },
    }
    a = (
        await c.post(
            f"/api/v1/rituals/{ritual['id']}/assignments", headers=auth(t[0]), json=command
        )
    ).json()
    o = next(
        x
        for x in (await c.get("/api/v1/ritual-occurrences", headers=auth(t[1]))).json()
        if x["assignment_id"] == a["id"]
    )
    edit = {"expected_version": a["revision"], "reward_version_ids": [], "currency_amount": 100}
    assert (
        await c.put(f"/api/v1/ritual-assignments/{a['id']}/rewards", headers=auth(t[1]), json=edit)
    ).status_code == 403
    changed = await c.put(
        f"/api/v1/ritual-assignments/{a['id']}/rewards", headers=auth(t[0]), json=edit
    )
    assert (
        changed.status_code == 200 and changed.json()["reward_policy_id"] != a["reward_policy_id"]
    )
    assert (
        await c.put(f"/api/v1/ritual-assignments/{a['id']}/rewards", headers=auth(t[0]), json=edit)
    ).status_code == 409
    path = f"/api/v1/ritual-occurrences/{o['id']}"
    o = (
        await c.post(
            path + "/report",
            headers=auth(t[1]),
            json={
                "expected_version": o["revision"],
                "idempotency_key": str(uuid4()),
                "text": "Done",
            },
        )
    ).json()
    reviews = await asyncio.gather(
        *(
            c.post(
                path + "/review",
                headers=auth(t[0]),
                json={"expected_version": o["revision"], "decision": "approved"},
            )
            for _ in range(2)
        )
    )
    assert sorted(x.status_code for x in reviews) == [200, 409]
    wallet = (await c.get(f"/api/v1/relations/{r['id']}/wallet", headers=auth(t[1]))).json()
    assert wallet["balance"] == 12
    assert len((await c.get("/api/v1/reward-grants", headers=auth(t[1]))).json()) == 1


async def test_migration_keeps_legacy_reward_policy_grant_and_history(api):
    import os

    c, app, ids, t, ritual, reward, r = await context(api)
    a = (
        await c.post(
            f"/api/v1/rituals/{ritual['id']}/assignments",
            headers=auth(t[0]),
            json={
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
            },
        )
    ).json()
    o = next(
        x
        for x in (await c.get("/api/v1/ritual-occurrences", headers=auth(t[1]))).json()
        if x["assignment_id"] == a["id"]
    )
    assert (
        await c.post(
            f"/api/v1/ritual-occurrences/{o['id']}/report",
            headers=auth(t[1]),
            json={
                "expected_version": o["revision"],
                "idempotency_key": str(uuid4()),
                "text": "Completed",
            },
        )
    ).status_code == 200
    before = (await c.get("/api/v1/reward-grants", headers=auth(t[1]))).json()

    async def migration(command, revision):
        process = await asyncio.create_subprocess_exec(
            "alembic",
            "-c",
            "backend/alembic.ini",
            command,
            revision,
            env={**os.environ, "DATABASE_URL": app.state.settings.database_url},
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        out, err = await process.communicate()
        assert process.returncode == 0, (out + err).decode()

    try:
        await migration("downgrade", "0018")
        await migration("upgrade", "head")
        after = (await c.get("/api/v1/reward-grants", headers=auth(t[1]))).json()
        assert len(after) == 1 and after[0]["id"] == before[0]["id"]
        assert after[0]["status"] == "offered" and after[0]["history"] == before[0]["history"]
        assignment = next(
            x
            for x in (await c.get("/api/v1/ritual-assignments", headers=auth(t[0]))).json()
            if x["id"] == a["id"]
        )
        assert assignment["reward_version_ids"] == [reward["version_id"]]
    finally:
        await migration("upgrade", "head")
