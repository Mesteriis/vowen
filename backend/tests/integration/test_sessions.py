import asyncio

from conftest import NOW
from sqlalchemy import func, select
from test_telegram_validation import signed

from vowen.modules.identity.models import User
from vowen.modules.identity.service import ProvisionUserCommand, create_user, set_user_active


async def provision(app, telegram_id=100000000001):
    async with app.state.sessions() as db:
        user = await create_user(
            db, ProvisionUserCommand(telegram_id=telegram_id, display_name="Synthetic"), NOW
        )
        await db.commit()
        return user.id


async def login(client, raw=None):
    return await client.post("/api/v1/auth/telegram/miniapp", json={"init_data": raw or signed()})


def auth(tokens):
    return {"Authorization": "Bearer " + tokens["access_token"]}


async def test_invalid_unknown_disabled_and_no_autoprovision(api):
    client, app = api
    assert (await login(client, "invalid")).status_code == 401
    unknown = await login(client)
    assert unknown.status_code == 403
    await provision(app)
    async with app.state.sessions() as db:
        await set_user_active(db, 100000000001, False, NOW)
        await db.commit()
    disabled = await login(client)
    assert disabled.status_code == 403
    assert disabled.json()["error"]["code"] == unknown.json()["error"]["code"]
    async with app.state.sessions() as db:
        assert await db.scalar(select(func.count()).select_from(User)) == 1


async def test_replay_reordered_and_concurrent(api):
    client, app = api
    await provision(app)
    proof = signed()
    responses = await asyncio.gather(
        login(client, proof), login(client, "&".join(reversed(proof.split("&"))))
    )
    assert sorted(r.status_code for r in responses) == [200, 401]


async def test_disable_revokes_live_access_even_after_reenable(api):
    client, app = api
    await provision(app)
    tokens = (await login(client)).json()
    assert (await client.get("/api/v1/me", headers=auth(tokens))).status_code == 200
    async with app.state.sessions() as db:
        await set_user_active(db, 100000000001, False, NOW)
        await db.commit()
    assert (await client.get("/api/v1/me", headers=auth(tokens))).status_code == 401
    async with app.state.sessions() as db:
        await set_user_active(db, 100000000001, True, NOW)
        await db.commit()
    assert (await client.get("/api/v1/me", headers=auth(tokens))).status_code == 401


async def test_refresh_rotation_reuse_revokes_family(api):
    client, app = api
    await provision(app)
    first = (await login(client)).json()
    rotated = await client.post(
        "/api/v1/auth/refresh", json={"refresh_token": first["refresh_token"]}
    )
    assert rotated.status_code == 200
    assert rotated.json()["refresh_token"] != first["refresh_token"]
    assert (
        await client.post("/api/v1/auth/refresh", json={"refresh_token": first["refresh_token"]})
    ).status_code == 401
    assert (await client.get("/api/v1/me", headers=auth(rotated.json()))).status_code == 401


async def test_session_list_delete_ownership_and_sanitized_errors(api):
    client, app = api
    await provision(app)
    await provision(app, 100000000002)
    a = (await login(client)).json()
    b = (await login(client, signed(100000000002))).json()
    listing = await client.get("/api/v1/sessions", headers=auth(a))
    assert len(listing.json()) == 1
    assert a["refresh_token"] not in listing.text
    assert (
        await client.delete("/api/v1/sessions/" + a["session_id"], headers=auth(b))
    ).status_code == 404
    assert (
        await client.delete("/api/v1/sessions/" + a["session_id"], headers=auth(a))
    ).status_code == 204
    assert (await client.get("/api/v1/me", headers=auth(a))).status_code == 401
    invalid = await client.post(
        "/api/v1/auth/refresh", json={"refresh_token": {"secret": "synthetic-marker"}}
    )
    assert invalid.status_code == 422
    assert "synthetic-marker" not in invalid.text
