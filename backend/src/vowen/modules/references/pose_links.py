"""Shared pose equipment and example participant compositions; no permissions implied."""

from collections import defaultdict
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from vowen.modules.references.models import PoseComposition, PoseDevice
from vowen.modules.references.schemas import ReferenceView


async def populate_pose_links(db: AsyncSession, views: list[ReferenceView]) -> list[ReferenceView]:
    ids = [view.uid for view in views]
    if not ids:
        return views
    devices: dict[UUID, list[UUID]] = defaultdict(list)
    compositions: dict[UUID, list[UUID]] = defaultdict(list)
    for pose_uid, device_uid in await db.execute(
        select(PoseDevice.pose_uid, PoseDevice.device_uid)
        .where(PoseDevice.pose_uid.in_(ids))
        .order_by(PoseDevice.device_uid)
    ):
        devices[pose_uid].append(device_uid)
    for pose_uid, composition_uid in await db.execute(
        select(PoseComposition.pose_uid, PoseComposition.composition_uid)
        .where(PoseComposition.pose_uid.in_(ids))
        .order_by(PoseComposition.composition_uid)
    ):
        compositions[pose_uid].append(composition_uid)
    for view in views:
        view.device_uids = devices[view.uid]
        view.composition_uids = compositions[view.uid]
    return views
