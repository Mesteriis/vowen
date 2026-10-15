from uuid import uuid4

import httpx
import pytest
from conftest import NOW
from pydantic import ValidationError
from sqlalchemy import func, select
from test_sessions import auth, provision

from vowen.core.config import Settings
from vowen.modules.identity.models import User
from vowen.modules.identity.service import set_user_active


@pytest.mark.parametrize(
    "override",
    [
        {"app_env": "production"},
        {"public_base_url": "https://vowen.example"},
        {"database_url": "postgresql+psycopg://user:password@localhost/vowen"},
        {"database_url": "postgresql+psycopg://user:password@10.0.0.1/vowen_dev"},
    ],
)
def test_debug_rejects_unsafe_settings(override):
    values = dict(
        app_env="development",
        debug_auth=True,
        database_url="postgresql+psycopg://user:password@127.0.0.1/vowen_dev",
        public_base_url="http://127.0.0.1:5176",
    )
    values.update(override)
    with pytest.raises(ValidationError):
        Settings(_env_file=None, **values)


async def test_disabled_debug_is_unavailable_without_db_access(api):
    client, app = api
    assert not (await client.get("/api/v1/instance")).json()["debug_auth_enabled"]
    # The guard runs before even attempting a transaction.
    original = app.state.sessions
    app.state.sessions = lambda: pytest.fail("disabled debug must not access the database")
    try:
        assert (await client.get("/api/v1/auth/debug/users")).status_code == 404
        assert (
            await client.post("/api/v1/auth/debug", json={"user_id": str(uuid4())})
        ).status_code == 404
    finally:
        app.state.sessions = original


@pytest.fixture
async def debug_client(api):
    _, app = api
    app.state.settings = Settings(
        _env_file=None,
        app_env="development",
        debug_auth=True,
        database_url=app.state.settings.database_url,
        public_base_url="http://127.0.0.1:5176",
        data_keyring_file=app.state.settings.data_keyring_file,
    )
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://127.0.0.1:5176",
        headers={"Origin": "http://127.0.0.1:5176"},
    ) as client:
        yield client, app


@pytest.mark.parametrize(
    "headers",
    [
        {"Host": "evil.example"},
        {"Origin": "https://evil.example"},
        {"Sec-Fetch-Site": "cross-site"},
        {"X-Forwarded-For": "10.0.0.25"},
    ],
)
async def test_debug_denies_nonlocal_browser_context(debug_client, headers):
    client, _ = debug_client
    assert (await client.get("/api/v1/auth/debug/users", headers=headers)).status_code == 404
    assert (
        await client.post("/api/v1/auth/debug", headers=headers, json={"user_id": str(uuid4())})
    ).status_code == 404


async def test_debug_denies_remote_peer_and_missing_origin(debug_client):
    client, app = debug_client
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app, client=("10.0.0.25", 1234)),
        base_url=str(client.base_url),
        headers=client.headers,
    ) as remote:
        assert (await remote.get("/api/v1/auth/debug/users")).status_code == 404
    client.headers.pop("Origin")
    assert (
        await client.post("/api/v1/auth/debug", json={"user_id": str(uuid4())})
    ).status_code == 404


async def test_debug_existing_users_normal_sessions_disable_and_no_auto_provision(debug_client):
    client, app = debug_client
    user_id = await provision(app)
    other_id = await provision(app, 100000000002)
    async with app.state.sessions() as db:
        await set_user_active(db, 100000000002, False, NOW)
        await db.commit()
    assert (await client.get("/api/v1/instance")).json()["debug_auth_enabled"]
    users = (await client.get("/api/v1/auth/debug/users")).json()
    assert users == [{"id": str(user_id), "display_name": "Synthetic"}]
    for denied_id in (uuid4(), other_id):
        response = await client.post("/api/v1/auth/debug", json={"user_id": str(denied_id)})
        assert response.status_code == 403
    tokens = (await client.post("/api/v1/auth/debug", json={"user_id": str(user_id)})).json()
    assert (await client.get("/api/v1/me", headers=auth(tokens))).json()["id"] == str(user_id)
    assert (await client.get("/api/v1/relations", headers=auth(tokens))).json() == []
    sessions = (await client.get("/api/v1/sessions", headers=auth(tokens))).json()
    assert sessions[0]["client"] == "debug"
    assert sessions[0]["device_label"] == "Local development"
    rotated = await client.post(
        "/api/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]}
    )
    assert rotated.status_code == 200
    tokens = rotated.json()
    assert (
        await client.delete("/api/v1/sessions/" + tokens["session_id"], headers=auth(tokens))
    ).status_code == 204
    assert (await client.get("/api/v1/me", headers=auth(tokens))).status_code == 401
    tokens = (await client.post("/api/v1/auth/debug", json={"user_id": str(user_id)})).json()
    async with app.state.sessions() as db:
        await set_user_active(db, 100000000001, False, NOW)
        await db.commit()
        assert await db.scalar(select(func.count()).select_from(User)) == 2
    assert (await client.get("/api/v1/me", headers=auth(tokens))).status_code == 401


async def test_debug_session_keeps_consent_and_pause_boundary(debug_client):
    from uuid import UUID

    from test_relations import accept, propose

    from vowen.core.crypto import init_keyring
    from vowen.core.errors import AppError
    from vowen.modules.auth.service import MemberPrincipal
    from vowen.modules.relations.policy import ResourceContext, authorize

    client, app = debug_client
    init_keyring(app.state.settings.data_keyring_file)
    ids = [await provision(app, 100000000001 + i) for i in range(2)]
    tokens = [
        (await client.post("/api/v1/auth/debug", json={"user_id": str(user_id)})).json()
        for user_id in ids
    ]
    principal = MemberPrincipal(ids[0], UUID(tokens[0]["session_id"]))
    resource = ResourceContext(ids[1], frozenset({ids[0]}))
    relation = (await propose(client, tokens[0], ids[0], ids[1])).json()
    first = (await accept(client, tokens[0], relation)).json()
    async with app.state.sessions() as db:
        with pytest.raises(AppError):
            await authorize(db, principal, "rules.assign", resource)
    active = (await accept(client, tokens[1], first)).json()
    async with app.state.sessions() as db:
        await authorize(db, principal, "rules.assign", resource)
        with pytest.raises(AppError):
            await authorize(db, principal, "rewards.grant", resource)
    paused = await client.post(
        "/api/v1/relations/" + active["id"] + "/pause",
        headers=auth(tokens[1]),
        json={"expected_version": active["version"]},
    )
    assert paused.status_code == 200
    async with app.state.sessions() as db:
        with pytest.raises(AppError):
            await authorize(db, principal, "rules.assign", resource)
