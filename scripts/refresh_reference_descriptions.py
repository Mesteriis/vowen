"""Refresh untouched v15 reference descriptions; never overwrite user changes or seed missing rows."""

import argparse
import asyncio
import os
from uuid import UUID

from sqlalchemy.exc import SQLAlchemyError
from vowen.core.database import check_schema, engine_for, sessions_for
from vowen.core.errors import AppError
from vowen.modules.references.description_refresh import refresh_reference_descriptions


async def run(actor: UUID) -> None:
    url = os.environ.get("DATABASE_URL")
    if not url:
        raise ValueError("DATABASE_URL is required")
    engine = engine_for(url)
    try:
        if not await check_schema(engine):
            raise ValueError("Apply Alembic migrations first")
        async with sessions_for(engine).begin() as db:
            result = await refresh_reference_descriptions(db, actor)
        print(result.model_dump_json())
    finally:
        await engine.dispose()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--actor", required=True, type=UUID)
    args = parser.parse_args()
    try:
        asyncio.run(run(args.actor))
    except AppError as error:
        parser.exit(1, f"Reference refresh rejected: {error.code}\n")
    except (ValueError, SQLAlchemyError):
        parser.exit(1, "Reference refresh failed; check schema, fixtures and connection.\n")


if __name__ == "__main__":
    main()
