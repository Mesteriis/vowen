import httpx

from vowen.core.config import Settings
from vowen.main import create_app


async def test_liveness_does_not_need_telegram():
    app = create_app(Settings(database_url="postgresql+psycopg://invalid:invalid@127.0.0.1:1/no"))
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="https://test"
    ) as client:
        assert (await client.get("/health/live")).status_code == 200
    await app.state.engine.dispose()


async def test_readiness_fails_for_unavailable_database():
    app = create_app(Settings(database_url="postgresql+psycopg://invalid:invalid@127.0.0.1:1/no"))
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="https://test"
    ) as client:
        response = await client.get("/health/ready")
        assert response.status_code == 503
        assert "invalid" not in response.text
    await app.state.engine.dispose()
