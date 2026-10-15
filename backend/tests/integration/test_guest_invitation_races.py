import asyncio
from datetime import timedelta
from uuid import uuid4

import httpx
from conftest import NOW
from sqlalchemy import func, select
from test_forms_versions import setup_forms

from vowen.modules.identity.models import User


async def guest_invite(api):
    c, app, ids, h, f = await setup_forms(api)
    p = "/api/v1/forms/" + f["id"]
    await c.post(p + "/publish", headers=h[0], json={"expected_version": 1})
    r = await c.post(p + "/invitations", headers=h[0], json={"reader_ids": [str(ids[2])]})
    assert r.status_code == 200
    return c, app, ids, h, r.json()


async def test_guest_exchange_csrf_receipt_scope_and_delete(api):
    c, app, ids, h, i = await guest_invite(api)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="https://test"
    ) as g:
        proof = {"public_id": i["id"], "token": i["link"].split("#token=")[1]}
        assert (await g.post("/api/v1/guest/invitations/exchange", json=proof)).status_code == 403
        opened = await g.post(
            "/api/v1/guest/invitations/exchange", headers={"Origin": "https://test"}, json=proof
        )
        assert opened.status_code == 200
        cookie = opened.headers["set-cookie"]
        assert "HttpOnly" in cookie and "Secure" in cookie and "SameSite=lax" in cookie
        csrf = {"Origin": "https://test", "X-CSRF-Token": opened.json()["csrf_token"]}
        assert (await g.get("/api/v1/me")).status_code == 401
        assert (
            await g.put("/api/v1/guest/draft", json={"answers": {"q": "secret"}})
        ).status_code == 403
        assert (
            await g.put("/api/v1/guest/draft", headers=csrf, json={"answers": {"q": "secret"}})
        ).status_code == 200
        retry = await g.post(
            "/api/v1/guest/invitations/exchange", headers={"Origin": "https://test"}, json=proof
        )
        assert retry.status_code == 200
        csrf["X-CSRF-Token"] = retry.json()["csrf_token"]
        assert retry.json()["answers"] == {"q": "secret"}
        assert (
            await c.post(
                "/api/v1/guest/invitations/exchange", headers={"Origin": "https://test"}, json=proof
            )
        ).status_code == 409
        submit = {"answers": {"q": "secret"}, "idempotency_key": str(uuid4()), "acknowledged": True}
        result = await g.post("/api/v1/guest/submit", headers=csrf, json=submit)
        assert result.status_code == 200
        sid = result.json()["id"]
        assert (await g.post("/api/v1/guest/submit", headers=csrf, json=submit)).json()["id"] == sid
        receipt = (await g.post("/api/v1/guest/receipt", headers=csrf)).json()
        # Independent receipt capability works after invitation expiry, never draft/submit.
        app.state.clock = type("Clock", (), {"now": lambda self: NOW + timedelta(days=8)})()
        c.cookies.clear()
        exchanged = await c.post(
            "/api/v1/guest/receipts/exchange", headers={"Origin": "https://test"}, json=receipt
        )
        assert exchanged.status_code == 200
        rh = {"Origin": "https://test", "X-CSRF-Token": exchanged.json()["csrf_token"]}
        assert (
            await c.put("/api/v1/guest/draft", headers=rh, json={"answers": {}})
        ).status_code == 403
        assert (await c.get("/api/v1/guest/submission")).json()["answers"] == {"q": "secret"}
        assert (await c.delete("/api/v1/guest/submission", headers=rh)).status_code == 204
        assert (await c.get("/api/v1/guest/submission")).status_code == 401
    async with app.state.sessions() as db:
        assert await db.scalar(select(func.count()).select_from(User)) == 3


async def test_submit_revoke_and_duplicate_exchange_are_serialized(api):
    c, app, ids, h, i = await guest_invite(api)
    proof = {"public_id": i["id"], "token": i["link"].split("#token=")[1]}

    async def open_one():
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="https://test"
        ) as g:
            r = await g.post(
                "/api/v1/guest/invitations/exchange", headers={"Origin": "https://test"}, json=proof
            )
            return r, g.cookies

    opened = await asyncio.gather(open_one(), open_one())
    assert sorted(r.status_code for r, _ in opened) == [200, 409]
    ok, cookies = next((r, j) for r, j in opened if r.status_code == 200)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="https://test", cookies=cookies
    ) as g:
        csrf = {"Origin": "https://test", "X-CSRF-Token": ok.json()["csrf_token"]}
        submitted, revoked = await asyncio.gather(
            g.post(
                "/api/v1/guest/submit",
                headers=csrf,
                json={
                    "answers": {"q": "race"},
                    "idempotency_key": str(uuid4()),
                    "acknowledged": True,
                },
            ),
            c.delete("/api/v1/forms/invitations/" + i["id"], headers=h[0]),
        )
        assert revoked.status_code == 204
        assert submitted.status_code in (200, 410)
        assert (
            await g.put("/api/v1/guest/draft", headers=csrf, json={"answers": {}})
        ).status_code == 410
