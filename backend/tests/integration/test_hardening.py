import asyncio

from sqlalchemy import text
from test_sessions import auth, login, provision


async def test_parallel_refresh_revokes_family(api):
    client, app = api
    await provision(app)
    tokens = (await login(client)).json()
    replies = await asyncio.gather(
        *[
            client.post("/api/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
            for _ in range(2)
        ]
    )
    assert sorted(r.status_code for r in replies) == [200, 401]
    assert (
        await client.get(
            "/api/v1/me", headers=auth(next(r.json() for r in replies if r.status_code == 200))
        )
    ).status_code == 401


async def test_readiness_schema_guard_and_headers(api):
    client, app = api
    assert (await client.get("/health/ready")).status_code == 200
    async with app.state.engine.begin() as conn:
        await conn.execute(text("UPDATE alembic_version SET version_num='incompatible'"))
    try:
        assert (await client.get("/health/ready")).status_code == 503
        assert (await client.get("/api/v1/me")).status_code == 503
    finally:
        async with app.state.engine.begin() as conn:
            await conn.execute(text("UPDATE alembic_version SET version_num='0006'"))
    response = await client.get("/health/live")
    assert response.headers["cache-control"] == "no-store"
    invalid = await client.post("/api/v1/auth/telegram/miniapp", content=b"{" + b"x" * 524288)
    assert invalid.status_code == 413


async def test_rate_limit_challenge_creation(api):
    client, _ = api
    statuses = []
    for _ in range(21):
        response = await client.post(
            "/api/v1/auth/android/challenges",
            json={"client_nonce": "a" * 43, "device_label": "Synthetic"},
        )
        statuses.append(response.status_code)
    assert statuses[-1] == 429
