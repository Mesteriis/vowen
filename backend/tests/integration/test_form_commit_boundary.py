import httpx
from sqlalchemy import event
from sqlalchemy.exc import OperationalError
from test_guest_invitation_races import guest_invite


async def test_failed_commit_never_returns_guest_cookie_or_activation_success(api):
    c, app, ids, h, i = await guest_invite(api)

    def fail_commit(connection):
        raise OperationalError(None, None, RuntimeError("synthetic commit failure"))

    event.listen(app.state.engine.sync_engine, "commit", fail_commit)
    try:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app, raise_app_exceptions=False),
            base_url="https://test",
        ) as guest:
            response = await guest.post(
                "/api/v1/guest/invitations/exchange",
                headers={"Origin": "https://test"},
                json={"public_id": i["id"], "token": i["link"].split("#token=")[1]},
            )
            assert response.status_code == 503
            assert "set-cookie" not in response.headers
    finally:
        event.remove(app.state.engine.sync_engine, "commit", fail_commit)
