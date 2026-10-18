import asyncio

from conftest import NOW
from sqlalchemy import func, select
from test_sessions import auth, login, provision
from test_telegram_validation import signed

from vowen.modules.identity.models import AdministratorEvent, User


async def setup_members(api):
    client, app = api
    first = await provision(app)
    second = await provision(app, 100000000002)
    a = auth((await login(client)).json())
    b = auth((await login(client, signed(100000000002))).json())
    return client, app, first, second, a, b


async def test_first_provisioned_member_is_only_automatic_admin_even_concurrently(api):
    _, app = api
    ids = await asyncio.gather(provision(app), provision(app, 100000000002))
    async with app.state.sessions() as db:
        users = list(await db.scalars(select(User).where(User.id.in_(ids))))
        assert sum(u.is_admin for u in users) == 1
        # Fresh sessions see the persisted state; this is not token-local or in-process state.
        admin_id = next(u.id for u in users if u.is_admin)
    async with app.state.sessions() as db:
        assert (await db.get(User, admin_id)).is_admin


async def test_admin_api_denies_non_admin_and_self_promotion(api):
    client, _, first, second, a, b = await setup_members(api)
    assert (await client.get("/api/v1/administration")).status_code == 401
    assert (await client.get("/api/v1/administration", headers=b)).status_code == 403
    me = (await client.get("/api/v1/me", headers=b)).json()
    assert me["is_admin"] is False
    malicious = await client.patch(
        "/api/v1/me/preferences",
        headers=b,
        json={"expected_version": me["profile_version"], "is_admin": True},
    )
    assert malicious.status_code == 422
    # Editable D/s labels cannot grant administrative authority.
    assert (
        await client.patch(
            "/api/v1/me/preferences",
            headers=b,
            json={
                "expected_version": me["profile_version"],
                "profile_labels": ["dominant", "switch"],
            },
        )
    ).status_code == 200
    assert (await client.get("/api/v1/administration", headers=b)).status_code == 403
    view = (await client.get("/api/v1/administration", headers=a)).json()
    assert all(set(row) == {"id", "display_name", "is_admin"} for row in view["members"])
    for action in ["grant", "transfer"]:
        assert (
            await client.post(
                f"/api/v1/administration/administrators/{first}/{action}",
                headers=b,
                json={"expected_revision": view["revision"]},
            )
        ).status_code == 403
    assert str(second) in {row["id"] for row in view["members"]}


async def test_grant_and_transfer_use_current_authority_and_preserve_personal_access(api):
    client, app, first, second, a, b = await setup_members(api)
    revision = (await client.get("/api/v1/administration", headers=a)).json()["revision"]
    grant_url = f"/api/v1/administration/administrators/{second}/grant"
    assert (
        await client.post(grant_url, headers=a, json={"expected_revision": revision})
    ).status_code == 204
    assert (await client.get("/api/v1/me", headers=a)).json()["is_admin"] is True
    assert (await client.get("/api/v1/me", headers=b)).json()["is_admin"] is True
    # Old revision cannot mutate membership again.
    transfer_url = f"/api/v1/administration/administrators/{second}/transfer"
    assert (
        await client.post(transfer_url, headers=a, json={"expected_revision": revision})
    ).status_code == 409
    view = (await client.get("/api/v1/administration", headers=a)).json()
    # Granting an existing administrator is idempotent at the current revision.
    assert (
        await client.post(grant_url, headers=a, json={"expected_revision": view["revision"]})
    ).status_code == 204
    assert (await client.get("/api/v1/administration", headers=a)).json() == view
    assert (
        await client.post(transfer_url, headers=a, json={"expected_revision": view["revision"]})
    ).status_code == 204
    assert (await client.get("/api/v1/administration", headers=a)).status_code == 403
    assert (await client.get("/api/v1/administration", headers=b)).status_code == 200
    for endpoint in ["/me", "/me/notifications", "/sessions"]:
        assert (await client.get("/api/v1" + endpoint, headers=a)).status_code == 200
    # Already-issued access token loses administrator power immediately after transfer.
    assert (
        await client.post(
            f"/api/v1/administration/administrators/{first}/grant",
            headers=a,
            json={"expected_revision": view["revision"] + 1},
        )
    ).status_code == 403
    async with app.state.sessions() as db:
        assert await db.scalar(select(func.count()).select_from(AdministratorEvent)) == 2


async def test_simultaneous_transfers_cannot_remove_every_administrator(api):
    client, app, _, second, a, b = await setup_members(api)
    first = (await client.get("/api/v1/me", headers=a)).json()["id"]
    revision = (await client.get("/api/v1/administration", headers=a)).json()["revision"]
    await client.post(
        f"/api/v1/administration/administrators/{second}/grant",
        headers=a,
        json={"expected_revision": revision},
    )
    revision = (await client.get("/api/v1/administration", headers=a)).json()["revision"]
    responses = await asyncio.gather(
        client.post(
            f"/api/v1/administration/administrators/{second}/transfer",
            headers=a,
            json={"expected_revision": revision},
        ),
        client.post(
            f"/api/v1/administration/administrators/{first}/transfer",
            headers=b,
            json={"expected_revision": revision},
        ),
    )
    assert sorted(r.status_code for r in responses) == [204, 409]
    async with app.state.sessions() as db:
        assert await db.scalar(select(func.count()).select_from(User).where(User.is_admin)) == 1


async def test_invalid_targets_and_failed_commands_do_not_change_roles_or_revision(api):
    from uuid import uuid4

    from vowen.modules.identity.service import set_user_active

    client, app, first, second, a, _ = await setup_members(api)
    before = (await client.get("/api/v1/administration", headers=a)).json()
    for target, expected in [(first, 422), (uuid4(), 404)]:
        response = await client.post(
            f"/api/v1/administration/administrators/{target}/transfer",
            headers=a,
            json={"expected_revision": before["revision"]},
        )
        assert response.status_code == expected
    assert (await client.get("/api/v1/administration", headers=a)).json() == before
    async with app.state.sessions() as db, db.begin():
        await set_user_active(db, 100000000002, False, NOW)
    current = (await client.get("/api/v1/administration", headers=a)).json()
    assert str(second) not in {row["id"] for row in current["members"]}
    response = await client.post(
        f"/api/v1/administration/administrators/{second}/transfer",
        headers=a,
        json={"expected_revision": current["revision"]},
    )
    assert response.status_code == 404
    async with app.state.sessions() as db:
        assert (await db.get(User, first)).is_admin
        assert await db.scalar(select(func.count()).select_from(AdministratorEvent)) == 0
