"""Shared practice-to-equipment links; relationship-specific dictionaries stay private."""

from collections import defaultdict
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from vowen.core.errors import AppError
from vowen.modules.references.models import BodyPart, Device, PracticeBodyPart, PracticeDevice
from vowen.modules.references.schemas import ReferenceView


async def populate_links(db: AsyncSession, views: list[ReferenceView]) -> list[ReferenceView]:
    ids = [view.uid for view in views]
    if not ids:
        return views
    devices: dict[UUID, list[UUID]] = defaultdict(list)
    parts: dict[UUID, list[UUID]] = defaultdict(list)
    for practice_uid, device_uid in await db.execute(
        select(PracticeDevice.practice_uid, PracticeDevice.device_uid)
        .where(PracticeDevice.practice_uid.in_(ids))
        .order_by(PracticeDevice.device_uid)
    ):
        devices[practice_uid].append(device_uid)
    for practice_uid, part_uid in await db.execute(
        select(PracticeBodyPart.practice_uid, PracticeBodyPart.body_part_uid)
        .where(PracticeBodyPart.practice_uid.in_(ids))
        .order_by(PracticeBodyPart.body_part_uid)
    ):
        parts[practice_uid].append(part_uid)
    for view in views:
        view.device_uids = devices[view.uid]
        view.body_part_uids = parts[view.uid]
    return views


async def add_links(
    db: AsyncSession, practice_uid: UUID, device_uids: list[UUID], body_part_uids: list[UUID]
) -> None:
    devices = set(device_uids)
    parts = set(body_part_uids)
    found_devices = set(await db.scalars(select(Device.uid).where(Device.uid.in_(devices))))
    found_parts = set(await db.scalars(select(BodyPart.uid).where(BodyPart.uid.in_(parts))))
    if devices != found_devices or parts != found_parts:
        raise AppError(422, "INVALID_PRACTICE_EQUIPMENT")
    db.add_all(PracticeDevice(practice_uid=practice_uid, device_uid=uid) for uid in devices)
    db.add_all(PracticeBodyPart(practice_uid=practice_uid, body_part_uid=uid) for uid in parts)
    await db.flush()
