from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

SCHEMA_REVISION = "0003"


class Base(DeclarativeBase):
    pass


def engine_for(url: str) -> AsyncEngine:
    return create_async_engine(
        url, echo=False, hide_parameters=True, connect_args={"connect_timeout": 3}
    )


async def check_schema(engine: AsyncEngine) -> bool:
    async with engine.connect() as conn:
        revision = await conn.scalar(text("SELECT version_num FROM alembic_version"))
        return revision == SCHEMA_REVISION


def sessions_for(engine: AsyncEngine) -> async_sessionmaker:
    return async_sessionmaker(engine, expire_on_commit=False)
