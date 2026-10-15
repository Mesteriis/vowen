import asyncio
from alembic import context
from vowen.core.config import Settings
from vowen.core.database import Base, engine_for


def run_sync(connection):
    context.configure(connection=connection, target_metadata=Base.metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run():
    engine = engine_for(Settings().database_url)
    async with engine.connect() as connection:
        await connection.run_sync(run_sync)
    await engine.dispose()


asyncio.run(run())
