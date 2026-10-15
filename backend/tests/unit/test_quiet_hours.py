from datetime import datetime

import pytest

from vowen.modules.notifications.preferences import quiet_until


@pytest.mark.parametrize(
    ("now", "zone", "start", "end", "expected"),
    [
        ("2026-10-15T10:00:00+00:00", "UTC", 540, 660, "2026-10-15T11:00:00+00:00"),
        ("2026-10-15T11:00:00+00:00", "UTC", 540, 660, "2026-10-15T11:00:00+00:00"),
        ("2026-10-15T23:30:00+00:00", "UTC", 1320, 480, "2026-10-16T08:00:00+00:00"),
        ("2026-10-16T07:59:00+00:00", "UTC", 1320, 480, "2026-10-16T08:00:00+00:00"),
        ("2026-10-25T00:15:00+00:00", "Europe/Madrid", 60, 150, "2026-10-25T01:30:00+00:00"),
        ("2026-10-25T00:45:00+00:00", "Europe/Madrid", 60, 150, "2026-10-25T01:30:00+00:00"),
        ("2026-10-25T01:15:00+00:00", "Europe/Madrid", 60, 150, "2026-10-25T01:30:00+00:00"),
        ("2026-03-29T00:45:00+00:00", "Europe/Madrid", 60, 150, "2026-03-29T01:30:00+00:00"),
    ],
)
def test_quiet_boundaries_and_dst(now, zone, start, end, expected):
    assert quiet_until(
        datetime.fromisoformat(now), zone, True, start, end
    ) == datetime.fromisoformat(expected)
