from sqlalchemy import text
from test_journal_privacy import edit_body
from test_relations import members
from test_sessions import auth

INK = {
    "version": 1,
    "strokes": [
        {
            "color": "ivory",
            "width": 0.003,
            "points": [{"x": 0.1, "y": 0.2, "p": 0.5}, {"x": 0.4, "y": 0.3, "p": 0.8}],
        }
    ],
}


async def test_handwriting_only_is_plain_private_and_roundtrips(api):
    client, app = api
    ids, tokens = await members(client, app, 2)
    body = {"date": "2026-10-15", "title": "Ink entry", "text": "", "handwriting": INK}
    response = await client.post("/api/v1/journal", headers=auth(tokens[0]), json=body)
    assert response.status_code == 200
    e = response.json()
    assert e["handwriting"] == INK and e["visibility"] == "private"
    assert (
        await client.get("/api/v1/journal/" + e["id"], headers=auth(tokens[1]))
    ).status_code == 404
    assert (await client.get("/api/v1/journal/export", headers=auth(tokens[1]))).json() == []
    assert (await client.get("/api/v1/journal/" + e["id"], headers=auth(tokens[0]))).json()[
        "handwriting"
    ] == INK
    async with app.state.sessions() as db:
        ciphertext = (await db.execute(text("SELECT ciphertext FROM journal_entries"))).scalar_one()
        assert b"Ink entry" in ciphertext and b'"strokes"' in ciphertext
    # Older clients editing text must not silently erase handwriting they don't know about.
    old_body = edit_body(e, text="Typed text added")
    old_body.pop("handwriting")
    e = (
        await client.patch("/api/v1/journal/" + e["id"], headers=auth(tokens[0]), json=old_body)
    ).json()
    assert e["handwriting"] == INK
    e = (
        await client.patch(
            "/api/v1/journal/" + e["id"],
            headers=auth(tokens[0]),
            json=edit_body(e, handwriting=None),
        )
    ).json()
    assert e["handwriting"] is None


async def test_new_date_is_today_and_existing_date_cannot_move(api):
    client, app = api
    ids, tokens = await members(client, app, 1)
    body = {"date": "2026-10-14", "title": "Date", "text": "Note"}
    assert (
        await client.post("/api/v1/journal", headers=auth(tokens[0]), json=body)
    ).status_code == 422
    e = (
        await client.post(
            "/api/v1/journal", headers=auth(tokens[0]), json={**body, "date": "2026-10-15"}
        )
    ).json()
    assert (
        await client.patch(
            "/api/v1/journal/" + e["id"],
            headers=auth(tokens[0]),
            json=edit_body(e, date="2026-10-14"),
        )
    ).status_code == 422


async def test_ink_is_bounded_and_cannot_embed_executable_content(api):
    client, app = api
    ids, tokens = await members(client, app, 1)
    base = {"date": "2026-10-15", "title": "Ink", "text": ""}
    for ink in [
        dict(INK, html="<script>"),
        {"version": 2, "strokes": []},
        {
            "version": 1,
            "strokes": [
                {"color": "ivory", "width": 0.003, "points": [{"x": 2, "y": 0.2, "p": 0.5}]}
            ],
        },
        {"version": 1, "strokes": []},
    ]:
        assert (
            await client.post(
                "/api/v1/journal", headers=auth(tokens[0]), json={**base, "handwriting": ink}
            )
        ).status_code == 422


async def test_today_uses_author_timezone_not_server_date(api):
    from vowen.modules.identity.models import UserPreferences

    client, app = api
    ids, tokens = await members(client, app, 1)
    async with app.state.sessions() as db, db.begin():
        prefs = await db.get(UserPreferences, ids[0])
        prefs.timezone = "Pacific/Pago_Pago"  # Test clock10UTC is still the previous day here.
    body = {"date": "2026-10-15", "title": "Local day", "text": "Note"}
    assert (
        await client.post("/api/v1/journal", headers=auth(tokens[0]), json=body)
    ).status_code == 422
    assert (
        await client.post(
            "/api/v1/journal", headers=auth(tokens[0]), json={**body, "date": "2026-10-14"}
        )
    ).status_code == 200
