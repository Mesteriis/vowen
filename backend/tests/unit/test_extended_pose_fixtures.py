import json
from pathlib import Path

from vowen.modules.references.fixtures import fixture_rows, link_rows


def test_remaining_pose_sections_have_explicit_dictionary_links():
    poses = fixture_rows("poses")
    categories = fixture_rows("pose-categories")
    assert len(poses) == 106 and len(categories) == 14
    category_ids = {row["extra"]["code"]: row["uid"] for row in categories}
    assert sum(row["category_uid"] == category_ids["supports"] for row in poses) == 3
    assert sum(row["category_uid"] == category_ids["equipment"] for row in poses) == 4
    assert sum(row["category_uid"] == category_ids["group"] for row in poses) == 3
    assert sum(row["category_uid"] == category_ids["protocol"] for row in poses) == 7
    for kind, field, catalogue, count in (
        ("pose-devices", "device_uid", "devices", 12),
        ("pose-compositions", "composition_uid", "participant-compositions", 9),
    ):
        links = link_rows(kind)
        assert len(links) == count
        assert len({tuple(sorted(row.items())) for row in links}) == count
        assert {row["pose_uid"] for row in links} <= {row["uid"] for row in poses}
        assert {row[field] for row in links} <= {row["uid"] for row in fixture_rows(catalogue)}
    selected = [row for row in poses if "modern-64" in row["extra"].get("collections", [])]
    assert len(selected) == 64


def test_remaining_pose_snapshot_only_adds_records_and_links():
    root = Path(__file__).resolve().parents[2]
    folder = root / "src/vowen/modules/references/fixtures"
    snapshot = json.loads((root / "migrations/fixtures/0050-pose-sections.json").read_text())
    assert len(snapshot["poses"]) == 14 and len(snapshot["pose-categories"]) == 3
    for kind in ("poses", "pose-categories"):
        previous = json.loads((folder / f"v19/{kind}.json").read_text())
        current = json.loads(json.dumps(fixture_rows(kind), default=str))
        assert current == previous + snapshot[kind]
    for kind in ("pose-devices", "pose-compositions"):
        assert snapshot[kind] == json.loads(json.dumps(link_rows(kind), default=str))
