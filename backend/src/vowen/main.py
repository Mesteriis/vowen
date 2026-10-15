import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError
from starlette.exceptions import HTTPException

from vowen.core.clock import Clock
from vowen.core.config import Settings
from vowen.core.database import check_schema, engine_for, sessions_for
from vowen.core.errors import AppError
from vowen.core.http_safety import HttpSafety
from vowen.core.maintenance import maintenance_loop
from vowen.modules.auth.router import router
from vowen.modules.auth.schemas import ErrorResponse
from vowen.modules.forms.router import router as forms_router
from vowen.modules.relations.router import router as relations_router
from vowen.modules.rituals.router import router as rituals_router
from vowen.modules.rules.router import router as rules_router


def create_app(settings: Settings) -> FastAPI:
    engine = engine_for(settings.database_url)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        stop = asyncio.Event()
        task = asyncio.create_task(maintenance_loop(sessions_for(engine), stop))
        try:
            yield
        finally:
            stop.set()
            await task
            await engine.dispose()

    app = FastAPI(
        title="Vowen",
        version="0.1.0",
        lifespan=lifespan,
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
        responses={
            status: {"model": ErrorResponse} for status in (401, 403, 404, 409, 413, 422, 429, 503)
        },
    )
    app.add_middleware(HttpSafety)
    app.state.clock = Clock()
    app.include_router(router)
    app.include_router(relations_router)
    app.include_router(forms_router)
    app.include_router(rules_router)
    app.include_router(rituals_router)

    @app.exception_handler(AppError)
    async def app_error(request: Request, error: AppError) -> JSONResponse:
        return JSONResponse(
            {"error": {"code": error.code, "message": error.code, "request_id": str(uuid4())}},
            status_code=error.status,
        )

    @app.exception_handler(HTTPException)
    async def http_error(request: Request, error: HTTPException) -> JSONResponse:
        return JSONResponse(
            {
                "error": {
                    "code": "HTTP_" + str(error.status_code),
                    "message": "Request unavailable",
                    "request_id": str(uuid4()),
                }
            },
            status_code=error.status_code,
        )

    @app.exception_handler(SQLAlchemyError)
    async def database_error(request: Request, error: SQLAlchemyError) -> JSONResponse:
        return JSONResponse(
            {
                "error": {
                    "code": "UNAVAILABLE",
                    "message": "Unavailable",
                    "request_id": str(uuid4()),
                }
            },
            status_code=503,
        )

    @app.exception_handler(RequestValidationError)
    async def invalid_input(request: Request, error: RequestValidationError) -> JSONResponse:
        return JSONResponse(
            {
                "error": {
                    "code": "INVALID_INPUT",
                    "message": "Invalid input",
                    "request_id": str(uuid4()),
                }
            },
            status_code=422,
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
