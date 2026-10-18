from uuid import UUID, uuid4

import pytest
from test_sessions import auth, login, provision
from test_telegram_validation import signed

from vowen.core.crypto import init_keyring
from vowen.core.errors import AppError
from vowen.modules.auth.service import GuestPrincipal, MemberPrincipal, OperatorContext
from vowen.modules.relations.policy import ResourceContext, authorize


async def members(client, app, count=4):
    init_keyring(app.state.settings.data_keyring_file)
    ids, tokens = [], []
    for i in range(count):
        ids.append(await provision(app, 100000000001 + i))
        tokens.append((await login(client, signed(100000000001 + i))).json())
    return ids, tokens


async def propose(client, token, dominant, submissive):
    return await client.post(
        "/api/v1/relations",
        headers=auth(token),
        json={
            "dominant_user_id": str(dominant),
            "submissive_user_id": str(submissive),
            "scopes": ["rules.assign"],
            "agreement_text": "synthetic-private-agreement",
        },
    )


async def accept(client, token, relation):
    return await client.post(
        "/api/v1/relations/" + relation["id"] + "/accept",
        headers=auth(token),
        json={
            "expected_version": relation["version"],
            "relation_version_id": relation["relation_version_id"],
        },
    )


async def test_explicit_consents_scopes_acl_nontransitive_pause_resume(api):
    client, app = api
    ids, tokens = await members(client, app)
    assert (await propose(client, tokens[0], ids[0], ids[0])).status_code == 422
    assert (await propose(client, tokens[2], ids[0], ids[1])).status_code == 403
    relation = (await propose(client, tokens[0], ids[0], ids[1])).json()
    assert relation["status"] == "proposed"
    first = (await accept(client, tokens[0], relation)).json()
    assert first["status"] == "proposed"
    assert (await accept(client, tokens[1], relation)).status_code == 409
    active = (await accept(client, tokens[1], first)).json()
    assert active["status"] == "active"
    second = (await propose(client, tokens[1], ids[1], ids[2])).json()
    second = (await accept(client, tokens[1], second)).json()
    assert (await accept(client, tokens[2], second)).json()["status"] == "active"
    async with app.state.sessions() as db:
        member = MemberPrincipal(ids[0], UUID(tokens[0]["session_id"]))
        await authorize(db, member, "rules.assign", ResourceContext(ids[1], frozenset({ids[0]})))
        for principal, action, target, acl in [
            (member, "rules.assign", ids[2], {ids[0]}),
            (member, "rules.assign", ids[3], {ids[0]}),
            (member, "journal.read", ids[1], {ids[0]}),
            (member, "rules.assign", ids[1], set()),
            (GuestPrincipal(uuid4()), "rules.assign", ids[1], {ids[0]}),
            (OperatorContext(), "rules.assign", ids[1], {ids[0]}),
        ]:
            with pytest.raises(AppError):
                await authorize(db, principal, action, ResourceContext(target, frozenset(acl)))
    outsider = await client.get("/api/v1/relations", headers=auth(tokens[3]))
    assert outsider.json() == []
    paused = (
        await client.post(
            "/api/v1/relations/" + active["id"] + "/pause",
            headers=auth(tokens[1]),
            json={"expected_version": active["version"]},
        )
    ).json()
    assert paused["status"] == "paused"
    async with app.state.sessions() as db:
        with pytest.raises(AppError):
            await authorize(
                db, member, "rules.assign", ResourceContext(ids[1], frozenset({ids[0]}))
            )
    resumed = (
        await client.post(
            "/api/v1/relations/" + active["id"] + "/resume",
            headers=auth(tokens[0]),
            json={"expected_version": paused["version"]},
        )
    ).json()
    assert resumed["relation_version_id"] != active["relation_version_id"]
    resumed = (await accept(client, tokens[0], resumed)).json()
    assert resumed["status"] == "proposed"
    resumed = (await accept(client, tokens[1], resumed)).json()
    assert resumed["status"] == "active"
    assert (await client.post("/api/v1/me/pause", headers=auth(tokens[1]))).status_code == 204
    async with app.state.sessions() as db:
        with pytest.raises(AppError):
            await authorize(
                db, member, "rules.assign", ResourceContext(ids[1], frozenset({ids[0]}))
            )
    assert (await client.get("/api/v1/me", headers=auth(tokens[1]))).status_code == 200
    assert (await client.post("/api/v1/me/resume", headers=auth(tokens[1]))).status_code == 204


async def test_scope_expansion_new_version_and_ciphertext(api):
    client, app = api
    ids, tokens = await members(client, app, 2)
    relation = (await propose(client, tokens[0], *ids)).json()
    relation = (await accept(client, tokens[0], relation)).json()
    relation = (await accept(client, tokens[1], relation)).json()
    updated = await client.post(
        "/api/v1/relations/" + relation["id"] + "/versions",
        headers=auth(tokens[0]),
        json={
            "expected_version": relation["version"],
            "scopes": ["rules.assign", "rewards.grant"],
            "agreement_text": "changed-synthetic-text",
        },
    )
    assert updated.status_code == 200
    assert updated.json()["status"] == "proposed"
    assert (await accept(client, tokens[1], relation)).status_code == 409
    from sqlalchemy import text

    async with app.state.engine.connect() as conn:
        payloads = (
            (await conn.execute(text("SELECT ciphertext FROM relation_versions"))).scalars().all()
        )
        assert all(b"synthetic" in bytes(p) for p in payloads)
