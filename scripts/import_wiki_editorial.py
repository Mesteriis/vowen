"""Publish the checked-in Russian Wiki articles as an explicitly named administrator.

Requires DATABASE_URL and --actor UUID. Default: add missing standalone articles.
With --devices: upgrade only pristine canonical device stubs, retaining their history;
with --practices: do the same for the supplied practice articles.
With --poses: expand the supplied pose articles.
With --catalogues: add missing publications from the other reference catalogues.
With --refresh-poses: review sources/links on unchanged pose articles.
With --refresh-devices: review sources/links on unchanged device articles.
With --refresh-practices: review sources/links on unchanged practice articles.
With --refresh-editorial: upgrade unchanged prior editorial publications with sources.
Create missing pages. Drafts, manual changes and archives are preserved.
No participants or reference rows are changed.
"""

import argparse
import asyncio
import os
from uuid import UUID

from sqlalchemy.exc import SQLAlchemyError
from vowen.core.database import check_schema, engine_for, sessions_for
from vowen.core.errors import AppError
from vowen.modules.wiki.catalogue_articles import seed_catalogue_articles
from vowen.modules.wiki.device_articles import seed_device_articles
from vowen.modules.wiki.device_review import refresh_device_pages
from vowen.modules.wiki.editorial import seed_editorial_pages
from vowen.modules.wiki.editorial_refresh import refresh_editorial_pages
from vowen.modules.wiki.pose_articles import seed_pose_articles
from vowen.modules.wiki.pose_review import refresh_pose_pages
from vowen.modules.wiki.practice_articles import seed_practice_articles
from vowen.modules.wiki.practice_review import refresh_practice_pages


async def run(
    actor: UUID, *, devices: bool = False, practices: bool = False, poses: bool = False,
    refresh_editorial: bool = False, catalogues: bool = False, refresh_practices: bool = False,
    refresh_devices: bool = False, refresh_poses: bool = False,
) -> None:
    if sum((devices, practices, poses, refresh_editorial, catalogues, refresh_practices, refresh_devices, refresh_poses)) > 1:
        raise ValueError("Choose one content import mode")
    url = os.environ.get("DATABASE_URL")
    if not url:
        raise ValueError("DATABASE_URL is required")
    engine = engine_for(url)
    try:
        if not await check_schema(engine):
            raise ValueError("Apply the current Alembic migrations before importing Wiki")
        async with sessions_for(engine).begin() as db:
            if refresh_poses:
                output = (await refresh_pose_pages(db, actor)).model_dump_json()
            elif refresh_devices:
                output = (await refresh_device_pages(db, actor)).model_dump_json()
            elif refresh_practices:
                output = (await refresh_practice_pages(db, actor)).model_dump_json()
            elif catalogues:
                output = (await seed_catalogue_articles(db, actor)).model_dump_json()
            elif refresh_editorial:
                output = (await refresh_editorial_pages(db, actor)).model_dump_json()
            elif devices:
                output = (await seed_device_articles(db, actor)).model_dump_json()
            elif practices:
                output = (await seed_practice_articles(db, actor)).model_dump_json()
            elif poses:
                output = (await seed_pose_articles(db, actor)).model_dump_json()
            else:
                output = (await seed_editorial_pages(db, actor)).model_dump_json()
        print(output)
    finally:
        await engine.dispose()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--actor", required=True, type=UUID, help="Existing active administrator UUID")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--devices", action="store_true", help="Expand untouched device stubs")
    mode.add_argument("--practices", action="store_true", help="Expand untouched practice stubs")
    mode.add_argument("--poses", action="store_true", help="Expand untouched pose stubs")
    mode.add_argument(
        "--refresh-editorial", action="store_true",
        help="Add sources only to unchanged prior editorial publications",
    )
    mode.add_argument("--catalogues", action="store_true", help="Add other catalogue articles")
    mode.add_argument(
        "--refresh-practices", action="store_true",
        help="Review sources and links only on unchanged original practice articles",
    )
    mode.add_argument(
        "--refresh-devices", action="store_true",
        help="Review sources and links only on unchanged original device articles",
    )
    mode.add_argument(
        "--refresh-poses", action="store_true",
        help="Review sources and links only on unchanged original pose articles",
    )
    args = parser.parse_args()
    try:
        asyncio.run(run(
            args.actor, devices=args.devices, practices=args.practices, poses=args.poses,
            refresh_editorial=args.refresh_editorial, catalogues=args.catalogues,
            refresh_practices=args.refresh_practices, refresh_devices=args.refresh_devices,
            refresh_poses=args.refresh_poses,
        ))
    except AppError as error:
        parser.exit(1, f"Wiki import rejected: {error.code}\n")
    except (ValueError, SQLAlchemyError):
        # Do not print connection strings, query parameters or sensitive database diagnostics.
        parser.exit(1, "Wiki import failed; check schema, fixtures and database connection.\n")


if __name__ == "__main__":
    main()
