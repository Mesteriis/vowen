from collections.abc import Iterator
from datetime import UTC, date, datetime, timedelta
from zoneinfo import ZoneInfo

from vowen.modules.rituals.schemas import Schedule


def local_slot(day: date, hour: int, minute: int, timezone: str) -> datetime:
    # fold=0 picks the first repeated instant. Roundtrip shifts a nonexistent
    # local time by its actual gap (including half-hour and full-day transitions).
    local = datetime(day.year, day.month, day.day, hour, minute, tzinfo=ZoneInfo(timezone), fold=0)
    return local.astimezone(UTC)


def slot_days(schedule: Schedule, start: date, end: date) -> Iterator[date]:
    day = max(start, schedule.start_date)
    while day <= end:
        if (
            schedule.kind == "daily"
            or (schedule.kind == "once" and day == schedule.start_date)
            or (schedule.kind == "weekly" and day.weekday() in schedule.weekdays)
        ):
            yield day
        day += timedelta(days=1)
