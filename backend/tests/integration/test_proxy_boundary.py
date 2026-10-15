import httpx
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware


async def test_only_trusted_proxy_gets_independent_client_rate_buckets(api):
    _, app = api
    proxy_app = ProxyHeadersMiddleware(app, trusted_hosts=["10.253.240.2"])
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=proxy_app, client=("10.253.240.2", 1000)),
        base_url="https://test",
    ) as client:
        for _ in range(20):
            assert (
                await client.post(
                    "/api/v1/auth/telegram/miniapp",
                    json={"init_data": "invalid"},
                    headers={"X-Forwarded-For": "192.0.2.1"},
                )
            ).status_code == 401
        assert (
            await client.post(
                "/api/v1/auth/telegram/miniapp",
                json={"init_data": "invalid"},
                headers={"X-Forwarded-For": "192.0.2.1"},
            )
        ).status_code == 429
        assert (
            await client.post(
                "/api/v1/auth/telegram/miniapp",
                json={"init_data": "invalid"},
                headers={"X-Forwarded-For": "192.0.2.2"},
            )
        ).status_code == 401
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=proxy_app, client=("192.0.2.3", 1000)),
        base_url="https://test",
    ) as client:
        for index in range(21):
            result = await client.post(
                "/api/v1/auth/telegram/miniapp",
                json={"init_data": "invalid"},
                headers={"X-Forwarded-For": f"198.51.100.{index}"},
            )
        assert result.status_code == 429
