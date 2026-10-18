import asyncio
from uuid import uuid4

from sqlalchemy import select, update
from test_economy import context
from test_relations import accept
from test_sessions import auth

from vowen.modules.identity.models import User
from vowen.modules.notifications.models import MemberDelivery
from vowen.modules.rewards.economy_models import CurrencyEntry


async def product(client, token, price=20):
    result = await client.post(
        "/api/v1/shop/products",
        headers=auth(token),
        json={
            "title": "A shared fixture",
            "description": "A complete fixture description",
            "conditions": "By mutual agreement",
            "cover": "cinema",
            "category": "together",
            "price": price,
            "audience_all": True,
        },
    )
    assert result.status_code == 200, result.text
    return result.json()


async def credit(client, token, rid, amount=50):
    result = await client.post(
        f"/api/v1/relations/{rid}/wallet/credits",
        headers=auth(token),
        json={"amount": amount, "comment": "Synthetic credit", "idempotency_key": str(uuid4())},
    )
    assert result.status_code == 200


async def decision(client, token, grant, action):
    return await client.post(
        f"/api/v1/reward-grants/{grant['id']}/transitions",
        headers=auth(token),
        json={"action": action, "expected_version": grant["revision"]},
    )


async def test_reservation_approval_snapshot_notices_and_redemption_race(api):
    c, app, ids, tokens, ritual, reward, relation = await context(api)
    item = await product(c, tokens[0])
    await credit(c, tokens[0], relation["id"])
    buy = f"/api/v1/shop/{item['id']}/purchases"
    body = {
        "relation_id": relation["id"],
        "expected_version": item["revision"],
        "idempotency_key": str(uuid4()),
    }
    results = await asyncio.gather(
        *(c.post(buy, headers=auth(tokens[1]), json=body) for _ in range(2))
    )
    assert [r.status_code for r in results] == [200, 200]
    grant = results[0].json()
    assert results[1].json()["id"] == grant["id"]
    assert grant["status"] == "pending_approval" and grant["purchase_amount"] == 20
    wallet_path = f"/api/v1/relations/{relation['id']}/wallet"
    wallet = (await c.get(wallet_path, headers=auth(tokens[1]))).json()
    assert (wallet["balance"], wallet["reserved"], wallet["total_balance"]) == (30, 20, 50)
    assert len(wallet["entries"]) == 1
    notices = (await c.get("/api/v1/reward-notices", headers=auth(tokens[0]))).json()
    assert any(n["grant_id"] == grant["id"] for n in notices)
    async with app.state.sessions() as db:
        deliveries = list(await db.scalars(select(MemberDelivery)))
        assert {row.user_id for row in deliveries} == {ids[0], ids[1]}
    assert (await decision(c, tokens[1], grant, "approve")).status_code == 403
    assert (await decision(c, tokens[2], grant, "approve")).status_code == 404
    # Editing the shared product never changes the reserved price or request content.
    changed = await c.patch(
        f"/api/v1/shop/products/{item['product_id']}",
        headers=auth(tokens[2]),
        json={
            "expected_version": item["product_revision"],
            "title": "Changed title",
            "description": "Changed description",
            "conditions": "Changed conditions",
            "cover": "breakfast",
            "category": "care",
            "price": 99,
            "audience_all": True,
        },
    )
    assert changed.status_code == 200
    await app.state.engine.dispose()
    assert (await c.get(wallet_path, headers=auth(tokens[1]))).json()["reserved"] == 20
    approved = await decision(c, tokens[0], grant, "approve")
    assert approved.status_code == 200
    approved = approved.json()
    assert approved["status"] == "accepted" and approved["title"] == item["title"]
    assert (await decision(c, tokens[0], grant, "approve")).status_code == 409
    wallet = (await c.get(wallet_path, headers=auth(tokens[1]))).json()
    assert (wallet["balance"], wallet["reserved"], wallet["total_balance"]) == (30, 0, 30)
    redeemed = await asyncio.gather(
        decision(c, tokens[0], approved, "redeem"), decision(c, tokens[1], approved, "redeem")
    )
    assert sorted(r.status_code for r in redeemed) == [200, 409]
    assert next(r.json() for r in redeemed if r.status_code == 200)["status"] == "redeemed"
    async with app.state.sessions() as db:
        debits = list(
            await db.scalars(select(CurrencyEntry).where(CurrencyEntry.kind == "purchase"))
        )
        assert len(debits) == 1 and debits[0].amount == -20


async def test_concurrent_reservations_rejection_and_withdrawal_release_coins(api):
    c, app, ids, tokens, ritual, reward, relation = await context(api)
    item = await product(c, tokens[0])
    await credit(c, tokens[0], relation["id"])
    buy = f"/api/v1/shop/{item['id']}/purchases"
    base = {"relation_id": relation["id"], "expected_version": item["revision"]}
    results = await asyncio.gather(
        *(
            c.post(buy, headers=auth(tokens[1]), json={**base, "idempotency_key": str(uuid4())})
            for _ in range(3)
        )
    )
    assert sorted(r.status_code for r in results) == [200, 200, 409]
    first, second = [r.json() for r in results if r.status_code == 200]
    wallet_path = f"/api/v1/relations/{relation['id']}/wallet"
    assert (await c.get(wallet_path, headers=auth(tokens[1]))).json()["reserved"] == 40
    assert (await decision(c, tokens[0], first, "reject")).status_code == 200
    assert (await c.get(wallet_path, headers=auth(tokens[1]))).json()["balance"] == 30
    # Consent revocation prevents approval, but cannot trap a buyer's reservation.
    assert (
        await c.post(
            f"/api/v1/relations/{relation['id']}/revoke",
            headers=auth(tokens[1]),
            json={"expected_version": relation["version"]},
        )
    ).status_code == 200
    assert (await decision(c, tokens[0], second, "approve")).status_code == 403
    assert (await decision(c, tokens[1], second, "cancel")).status_code == 200
    wallet = (await c.get(wallet_path, headers=auth(tokens[1]))).json()
    assert wallet["balance"] == wallet["total_balance"] == 50 and wallet["reserved"] == 0
    assert len(wallet["entries"]) == 1


async def test_switch_only_toggles_own_lower_and_dominant_manages_foreign_products(api):
    c, app, ids, tokens, ritual, reward, first = await context(api)
    item = await product(c, tokens[2])
    relations = (await c.get("/api/v1/relations", headers=auth(tokens[2]))).json()
    second = next(r for r in relations if r["dominant_user_id"] == str(ids[2]))
    second = (
        await c.post(
            f"/api/v1/relations/{second['id']}/versions",
            headers=auth(tokens[2]),
            json={
                "expected_version": second["version"],
                "agreement_text": "Explicit shop scope",
                "scopes": ["rewards.grant"],
            },
        )
    ).json()
    second = (await accept(c, tokens[2], second)).json()
    second = (await accept(c, tokens[1], second)).json()
    async with app.state.sessions() as db, db.begin():
        await db.execute(update(User).where(User.id == ids[2]).values(shop_role="switch"))
    # Profile labels cannot elevate canonical shop permissions.
    me = (await c.get("/api/v1/me", headers=auth(tokens[2]))).json()
    assert me["shop_role"] == "switch"
    assert (
        await c.patch(
            "/api/v1/me/preferences",
            headers=auth(tokens[2]),
            json={"expected_version": me["profile_version"], "shop_role": "dominant"},
        )
    ).status_code == 422
    assert (
        await c.patch(
            "/api/v1/me/preferences",
            headers=auth(tokens[2]),
            json={"expected_version": me["profile_version"], "profile_labels": ["dominant"]},
        )
    ).status_code == 200
    assert (
        await c.post(
            "/api/v1/shop/products",
            headers=auth(tokens[2]),
            json={"title": "Blocked", "description": "Blocked", "price": 1},
        )
    ).status_code == 403
    assert (
        await c.post(
            f"/api/v1/shop/products/{item['product_id']}/state",
            headers=auth(tokens[2]),
            json={"expected_version": item["product_revision"], "enabled": False},
        )
    ).status_code == 403
    assert (
        await c.post(
            f"/api/v1/shop/{item['id']}/purchases",
            headers=auth(tokens[2]),
            json={
                "relation_id": first["id"],
                "expected_version": item["revision"],
                "idempotency_key": str(uuid4()),
            },
        )
    ).status_code == 404
    private = (
        await c.post(
            "/api/v1/shop/products",
            headers=auth(tokens[0]),
            json={
                "title": "Private",
                "description": "Not shared with this switch",
                "price": 1,
                "audience_all": False,
            },
        )
    ).json()
    assert (
        await c.post(
            f"/api/v1/relations/{second['id']}/shop/products/{private['product_id']}/state",
            headers=auth(tokens[2]),
            json={"expected_version": 0, "enabled": True},
        )
    ).status_code == 404
    toggle = f"/api/v1/relations/{second['id']}/shop/products/{item['product_id']}/state"
    assert (
        await c.post(
            toggle, headers=auth(tokens[2]), json={"expected_version": 0, "enabled": False}
        )
    ).status_code == 200
    assert (
        await c.post(toggle, headers=auth(tokens[2]), json={"expected_version": 0, "enabled": True})
    ).status_code == 409
    hidden = (
        await c.get(f"/api/v1/shop/catalogue?relation_id={second['id']}", headers=auth(tokens[1]))
    ).json()
    assert all(row["product_id"] != item["product_id"] for row in hidden)
    visible = (
        await c.get(f"/api/v1/shop/catalogue?relation_id={first['id']}", headers=auth(tokens[1]))
    ).json()
    assert any(row["product_id"] == item["product_id"] for row in visible)
    own = (
        await c.get(f"/api/v1/shop/catalogue?relation_id={second['id']}", headers=auth(tokens[2]))
    ).json()
    disabled = next(row for row in own if row["product_id"] == item["product_id"])
    assert disabled["can_toggle"] and not disabled["active"] and not disabled["can_manage"]
    assert (
        await c.post(
            f"/api/v1/relations/{first['id']}/shop/products/{item['product_id']}/state",
            headers=auth(tokens[2]),
            json={"expected_version": 0, "enabled": False},
        )
    ).status_code == 404
    # Another dominant edits and globally disables a fixture regardless of its author.
    state = await c.post(
        f"/api/v1/shop/products/{item['product_id']}/state",
        headers=auth(tokens[0]),
        json={"expected_version": item["product_revision"], "enabled": False},
    )
    assert state.status_code == 200
    manager = (await c.get("/api/v1/shop/catalogue", headers=auth(tokens[0]))).json()
    disabled = next(row for row in manager if row["product_id"] == item["product_id"])
    assert disabled["can_manage"] and not disabled["active"]
    assert all(
        row["product_id"] != item["product_id"]
        for row in (await c.get("/api/v1/shop/catalogue", headers=auth(tokens[1]))).json()
    )
    archive = await c.post(
        f"/api/v1/shop/products/{item['product_id']}/archive",
        headers=auth(tokens[0]),
        json={"expected_version": state.json()["expected_version"]},
    )
    assert archive.status_code == 204
    assert all(
        row["product_id"] != item["product_id"]
        for row in (await c.get("/api/v1/shop/catalogue", headers=auth(tokens[0]))).json()
    )


async def test_pause_releases_pending_reserve_and_legacy_purchase_retry_does_not_charge(api):
    from uuid import UUID

    from vowen.core.crypto import PayloadCipher
    from vowen.modules.rewards import economy
    from vowen.modules.rewards.models import RewardGrant

    c, app, ids, tokens, ritual, reward, relation = await context(api)
    item = await product(c, tokens[0])
    await credit(c, tokens[0], relation["id"])
    buy = f"/api/v1/shop/{item['id']}/purchases"
    base = {"relation_id": relation["id"], "expected_version": item["revision"]}
    pending = (
        await c.post(
            buy,
            headers=auth(tokens[1]),
            json={
                **base,
                "idempotency_key": str(uuid4()),
            },
        )
    ).json()
    assert (await c.post("/api/v1/me/pause", headers=auth(tokens[1]))).status_code == 204
    assert (await decision(c, tokens[0], pending, "approve")).status_code == 403
    assert (await decision(c, tokens[1], pending, "cancel")).status_code == 200
    async with app.state.sessions() as db, db.begin():
        await db.execute(update(User).where(User.id == ids[1]).values(paused=False))
        # Simulate an already charged purchase created before migration 0022.
        legacy = RewardGrant(
            id=uuid4(),
            reward_version_id=UUID(item["reward_version_id"]),
            issuer_id=ids[0],
            recipient_id=ids[1],
            idempotency_key=uuid4(),
            revision=1,
            status="accepted",
            created_at=app.state.clock.now(),
        )
        db.add(legacy)
        await db.flush()
        key = uuid4()
        await economy.append(
            db,
            UUID(relation["id"]),
            ids[1],
            -20,
            "purchase",
            "",
            app.state.clock.now(),
            PayloadCipher(app.state.settings.data_keyring_file),
            key=key,
            grant_id=legacy.id,
            listing_id=UUID(item["id"]),
        )
        gid = str(legacy.id)
    retry = await c.post(buy, headers=auth(tokens[1]), json={**base, "idempotency_key": str(key)})
    assert retry.status_code == 200 and retry.json()["id"] == gid
    assert retry.json()["status"] == "accepted"
    redeemed = await decision(c, tokens[1], retry.json(), "redeem")
    assert redeemed.status_code == 200 and redeemed.json()["status"] == "redeemed"
    wallet = (
        await c.get(f"/api/v1/relations/{relation['id']}/wallet", headers=auth(tokens[1]))
    ).json()
    assert (wallet["balance"], wallet["reserved"], wallet["total_balance"]) == (30, 0, 30)
    assert len(wallet["entries"]) == 2


async def test_switch_buys_only_in_own_lower_context_and_keeps_upper_controls(api):
    c, app, ids, tokens, ritual, reward, lower = await context(api)
    upper = (
        await c.post(
            "/api/v1/relations",
            headers=auth(tokens[2]),
            json={
                "dominant_user_id": str(ids[2]),
                "submissive_user_id": str(ids[0]),
                "scopes": ["rewards.grant"],
                "agreement_text": "Switch buyer permission",
            },
        )
    ).json()
    upper = (await accept(c, tokens[2], upper)).json()
    upper = (await accept(c, tokens[0], upper)).json()
    async with app.state.sessions() as db, db.begin():
        await db.execute(update(User).where(User.id == ids[0]).values(shop_role="switch"))
    item = await product(c, tokens[2])
    await credit(c, tokens[2], upper["id"])
    own_upper = (
        await c.get(
            f"/api/v1/shop/catalogue?relation_id={lower['id']}",
            headers=auth(tokens[0]),
        )
    ).json()[0]
    assert own_upper["can_toggle"] and own_upper["purchase_relation_id"] is None
    own_lower = (
        await c.get(
            f"/api/v1/shop/catalogue?relation_id={upper['id']}",
            headers=auth(tokens[0]),
        )
    ).json()[0]
    assert own_lower["purchase_relation_id"] == upper["id"] and not own_lower["can_toggle"]
    assert not own_lower["can_manage"]
    general = (await c.get("/api/v1/shop/catalogue", headers=auth(tokens[0]))).json()[0]
    assert general["purchase_relation_id"] == upper["id"] and not general["can_toggle"]
    path = f"/api/v1/shop/{item['id']}/purchases"
    body = {
        "relation_id": upper["id"],
        "expected_version": item["revision"],
        "idempotency_key": str(uuid4()),
    }
    assert (
        await c.post(
            path,
            headers=auth(tokens[0]),
            json={
                **body,
                "relation_id": lower["id"],
            },
        )
    ).status_code == 403
    pending = await c.post(path, headers=auth(tokens[0]), json=body)
    assert pending.status_code == 200 and pending.json()["issuer_id"] == str(ids[2])
    wallet = f"/api/v1/relations/{upper['id']}/wallet"
    assert (await c.get(wallet, headers=auth(tokens[0]))).json()["reserved"] == 20
    approved = await decision(c, tokens[2], pending.json(), "approve")
    assert approved.status_code == 200
    assert (await decision(c, tokens[0], approved.json(), "redeem")).status_code == 200
    result = (await c.get(wallet, headers=auth(tokens[0]))).json()
    assert (result["balance"], result["reserved"], result["total_balance"]) == (30, 0, 30)
    assert (await c.get(f"/api/v1/relations/{lower['id']}/wallet", headers=auth(tokens[0]))).json()[
        "total_balance"
    ] == 0
