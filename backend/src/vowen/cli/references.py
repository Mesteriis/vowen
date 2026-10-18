import asyncio

import typer

from vowen.core.config import Settings
from vowen.core.database import check_schema, engine_for, sessions_for
from vowen.modules.references.fixtures import seed_references

references = typer.Typer(pretty_exceptions_enable=False)


async def seed() -> None:
    engine = engine_for(Settings().database_url)
    try:
        if not await check_schema(engine):
            raise RuntimeError("Run migrations first")
        async with sessions_for(engine)() as db, db.begin():
            await seed_references(db)
    finally:
        await engine.dispose()


@references.command("seed")
def seed_command() -> None:
    """Insert missing current reference fixtures without overwriting persisted entries."""
    asyncio.run(seed())
    typer.echo("Reference fixtures loaded; existing entries preserved")
