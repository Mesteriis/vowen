"""Readers are explicit snapshots; relationships and operators never imply readership."""

import asyncio

from sqlalchemy import text
from test_relations import accept, members, propose
from test_sessions import auth, provision


async def create(client, token, **extra):
    response = await client.post(
        "/api/v1/journal",
        headers=auth(token),
        json={
            "date": "2026-10-15",
            "title": "private-journal-title",
            "text": "private-journal-body",
            "tags": ["reflection"],
            "mood": "calm",
            **extra,
        },
    )
    assert response.status_code == 200
    return response.json()


def edit_body(entry, **changes):
    return {
        k: v
        for k, v in {**entry, **changes, "expected_version": entry["revision"]}.items()
        if k not in ("id", "author_id", "revision", "created_at", "updated_at")
    }


async def test_private_default_even_with_dominant_relation(api):
    client, app = api
    ids, tokens = await members(client, app, 3)
    app.state.settings.data_keyring_file.unlink()
    r = (await propose(client, tokens[0], ids[0], ids[1])).json()
    r = (await accept(client, tokens[0], r)).json()
    await accept(client, tokens[1], r)
    e = await create(client, tokens[1], published=True)
    assert e["visibility"] == "private" and e["reader_ids"] == []
    for token in (tokens[0], tokens[2]):
        for path in ("/api/v1/journal", "/api/v1/journal/export", "/api/v1/journal?search=private"):
            assert (await client.get(path, headers=auth(token))).json() == []
        assert (
            await client.get("/api/v1/journal/" + e["id"], headers=auth(token))
        ).status_code == 404
        assert (
            await client.patch(
                "/api/v1/journal/" + e["id"], headers=auth(token), json=edit_body(e, title="stolen")
            )
        ).status_code == 404
    async with app.state.engine.connect() as conn:
        payload = (await conn.execute(text("SELECT ciphertext FROM journal_entries"))).scalar_one()
        assert b"private-journal" in bytes(payload)


async def test_drafts_selected_reader_revoke_and_author_delete(api):
    client, app = api
    ids, tokens = await members(client, app, 3)
    e = await create(client, tokens[1], visibility="selected", reader_ids=[str(ids[0])])
    path = "/api/v1/journal/" + e["id"]
    assert (await client.get(path, headers=auth(tokens[0]))).status_code == 404
    e = (
        await client.patch(path, headers=auth(tokens[1]), json=edit_body(e, published=True))
    ).json()
    assert (await client.get(path, headers=auth(tokens[0]))).json()[
        "text"
    ] == "private-journal-body"
    assert (await client.patch(path, headers=auth(tokens[0]), json=edit_body(e))).status_code == 403
    assert (
        await client.post(
            path + "/delete", headers=auth(tokens[0]), json={"expected_version": e["revision"]}
        )
    ).status_code == 403
    outcomes = await asyncio.gather(
        *(
            client.patch(
                path, headers=auth(tokens[1]), json=edit_body(e, text="new text", reader_ids=[])
            )
            for _ in range(2)
        )
    )
    assert sorted(x.status_code for x in outcomes) == [200, 409]
    e = next(x.json() for x in outcomes if x.status_code == 200)
    assert (await client.get(path, headers=auth(tokens[0]))).status_code == 404
    assert (await client.get("/api/v1/journal/export", headers=auth(tokens[0]))).json() == []
    assert (
        await client.post(
            path + "/delete", headers=auth(tokens[1]), json={"expected_version": e["revision"]}
        )
    ).status_code == 204
    assert (await client.get(path, headers=auth(tokens[1]))).status_code == 404
    async with app.state.engine.connect() as conn:
        assert (await conn.execute(text("SELECT count(*) FROM journal_entries"))).scalar_one() == 0
        assert (await conn.execute(text("SELECT count(*) FROM journal_readers"))).scalar_one() == 0


async def test_snapshot_never_expands_on_join_or_content_edit(api):
    client, app = api
    ids, tokens = await members(client, app, 2)
    e = await create(client, tokens[0], visibility="all_current_members", published=True)
    assert e["reader_ids"] == [str(ids[1])]
    newcomer = await provision(app, 100000000003)
    from test_sessions import login
    from test_telegram_validation import signed

    new_token = (await login(client, signed(100000000003))).json()
    e = (
        await client.patch(
            "/api/v1/journal/" + e["id"], headers=auth(tokens[0]), json=edit_body(e, title="Edited")
        )
    ).json()
    assert e["reader_ids"] == [str(ids[1])]
    assert (await client.get("/api/v1/journal", headers=auth(new_token))).json() == []
    # Only an explicit author request may refresh the snapshot.
    e = (
        await client.patch(
            "/api/v1/journal/" + e["id"],
            headers=auth(tokens[0]),
            json=edit_body(e, refresh_audience=True),
        )
    ).json()
    assert set(e["reader_ids"]) == {str(ids[1]), str(newcomer)}


async def test_shared_filter_export_and_disabled_reader(api):
    client, app = api
    ids, tokens = await members(client, app, 3)
    await create(client, tokens[1], published=True)
    e = await create(
        client,
        tokens[1],
        published=True,
        visibility="selected",
        reader_ids=[str(ids[0])],
        title="<script>alert(1)</script>",
    )
    rows = (await client.get("/api/v1/journal?tag=reflection", headers=auth(tokens[0]))).json()
    assert [x["id"] for x in rows] == [e["id"]]
    assert (await client.get("/api/v1/journal?search=absent", headers=auth(tokens[0]))).json() == []
    await client.post("/api/v1/me/pause", headers=auth(tokens[0]))
    assert (await client.get("/api/v1/journal/export", headers=auth(tokens[0]))).json() == []
    # A paused author still has their own private diary.
    await client.post("/api/v1/me/pause", headers=auth(tokens[1]))
    assert len((await client.get("/api/v1/journal", headers=auth(tokens[1]))).json()) == 2


async def test_author_can_edit_or_remove_existing_paused_reader_without_regranting(api):
    client, app = api
    ids, tokens = await members(client, app, 3)
    e = await create(
        client, tokens[0], published=True, visibility="selected", reader_ids=[str(ids[1])]
    )
    assert (await client.post("/api/v1/me/pause", headers=auth(tokens[1]))).status_code == 204
    path = "/api/v1/journal/" + e["id"]
    response = await client.patch(
        path, headers=auth(tokens[0]), json=edit_body(e, text="Updated while reader paused")
    )
    assert response.status_code == 200
    e = response.json()
    assert (await client.get("/api/v1/journal", headers=auth(tokens[1]))).json() == []
    e = (await client.patch(path, headers=auth(tokens[0]), json=edit_body(e, reader_ids=[]))).json()
    assert e["reader_ids"] == []
    # Removed inactive readership cannot be added again without an active reader.
    assert (
        await client.patch(
            path, headers=auth(tokens[0]), json=edit_body(e, reader_ids=[str(ids[1])])
        )
    ).status_code == 422
