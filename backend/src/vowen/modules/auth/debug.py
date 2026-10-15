"""Explicit local development login; never alters authorization or creates users."""

from collections.abc import AsyncIterator

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from vowen.core.config import LOCAL_HOSTS
from vowen.core.errors import AppError


def debug_available(request: Request) -> bool:
    settings = request.app.state.settings
    origin = request.headers.get("origin")
    forwarded = request.headers.get("x-forwarded-for")
    return bool(
        settings.debug_auth
        and settings.app_env == "development"
        and request.client
        and request.client.host in LOCAL_HOSTS
        and request.url.hostname in LOCAL_HOSTS
        and request.headers.get("sec-fetch-site") != "cross-site"
        and (not forwarded or all(ip.strip() in LOCAL_HOSTS for ip in forwarded.split(",")))
        and (origin is None or origin == settings.public_base_url.rstrip("/"))
        and (request.method == "GET" or origin is not None)
    )


async def debug_transaction(request: Request) -> AsyncIterator[AsyncSession]:
    # Check before opening a transaction: disabled endpoints reveal no member data.
    if not debug_available(request):
        raise AppError(404, "NOT_FOUND")
    from vowen.modules.auth.router import transaction

    async for db in transaction(request):
        yield db
