"""Remove uv's rebuild-cache metadata from a read-only runtime installation.

Local source ctime is recorded in uv_cache.json even with SOURCE_DATE_EPOCH.
It is an incremental installer hint, not package runtime data. Preserve every
other wheel RECORD entry and remove the hint's corresponding entry as well.
"""

import csv
import sys
from pathlib import Path


def normalize(site_packages: Path) -> None:
    for cache in site_packages.glob("*.dist-info/uv_cache.json"):
        record = cache.parent / "RECORD"
        relative = cache.relative_to(site_packages).as_posix()
        with record.open(newline="") as stream:
            rows = list(csv.reader(stream))
        matching = [row for row in rows if row[0] == relative]
        if len(matching) != 1:
            raise ValueError("Unexpected installer cache RECORD")
        with record.open("w", newline="") as stream:
            csv.writer(stream).writerows(row for row in rows if row[0] != relative)
        cache.unlink()


if __name__ == "__main__":
    normalize(Path(sys.argv[1]))
