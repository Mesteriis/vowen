import time
from collections import deque
from collections.abc import MutableMapping
from uuid import uuid4

from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Message, Receive, Scope, Send


class HttpSafety:
    """Bounded per-process limiter, paired with a single API replica in Compose."""

    def __init__(self, app: ASGIApp):
        self.app = app
        self.windows: MutableMapping[tuple[str, str], deque[float]] = {}
        self.last_sweep = 0.0

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        now = time.monotonic()
        if now - self.last_sweep > 60:
            self.windows = {
                key: value for key, value in self.windows.items() if value and value[-1] > now - 60
            }
            self.last_sweep = now
        path = scope["path"]
        if (
            path.startswith("/api/v1/auth/")
            or path.startswith("/api/v1/guest/")
            or path.endswith("/submit")
        ):
            group = (
                "status"
                if path.endswith("/status")
                else "refresh"
                if path.endswith("/refresh")
                else "consume"
                if path.endswith("/consume")
                else path
            )
            key = (scope.get("client", ("unknown", 0))[0], group)
            if key not in self.windows and len(self.windows) >= 10000:
                await self.reject(scope, receive, send, 429, "RATE_LIMITED")
                return
            window = self.windows.setdefault(key, deque())
            while window and window[0] <= now - 60:
                window.popleft()
            limit = 120 if group in ("status", "refresh") else 20
            if len(window) >= limit:
                await self.reject(scope, receive, send, 429, "RATE_LIMITED")
                return
            window.append(now)
        body = bytearray()
        while True:
            message = await receive()
            if message["type"] == "http.disconnect":
                return
            body.extend(message.get("body", b""))
            if len(body) > 524288:
                await self.reject(scope, receive, send, 413, "BODY_TOO_LARGE")
                return
            if not message.get("more_body", False):
                break
        delivered = False

        async def replay() -> Message:
            nonlocal delivered
            if not delivered:
                delivered = True
                return {"type": "http.request", "body": bytes(body), "more_body": False}
            return await receive()

        async def safe_send(message: Message) -> None:
            if message["type"] == "http.response.start":
                headers = list(message.get("headers", []))
                headers.extend(
                    [
                        (b"cache-control", b"no-store"),
                        (b"x-content-type-options", b"nosniff"),
                        (b"referrer-policy", b"no-referrer"),
                        (b"x-robots-tag", b"noindex, nofollow"),
                    ]
                )
                message = {**message, "headers": headers}
            await send(message)

        await self.app(scope, replay, safe_send)

    @staticmethod
    async def reject(scope: Scope, receive: Receive, send: Send, status: int, code: str) -> None:
        response = JSONResponse(
            {"error": {"code": code, "message": code, "request_id": str(uuid4())}},
            status_code=status,
            headers={"Cache-Control": "no-store"},
        )
        await response(scope, receive, send)
