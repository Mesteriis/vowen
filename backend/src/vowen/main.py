from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError

from vowen.core.config import Settings
from vowen.core.database import check_schema, engine_for, sessions_for


def create_app(settings: Settings) -> FastAPI:
    engine = engine_for(settings.database_url)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        yield
        await engine.dispose()

    app = FastAPI(
        title="Vowen",
        version="0.1.0",
        lifespan=lifespan,
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
    )
    app.state.settings = settings
    app.state.engine = engine
    app.state.sessions = sessions_for(engine)

    @app.get("/health/live")
    async def live() -> dict[str, str]:
        return {"status": "alive"}

    @app.get("/health/ready")
    async def ready() -> JSONResponse:
        try:
            compatible = await check_schema(engine)
        except (SQLAlchemyError, OSError):
            compatible = False
        return JSONResponse(
            {"status": "ready" if compatible else "unavailable"},
            status_code=200 if compatible else 503,
        )

    return app


app = create_app(Settings())
