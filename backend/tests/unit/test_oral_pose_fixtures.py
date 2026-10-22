import json
from pathlib import Path

from vowen.modules.references.fixtures import fixture_rows


def test_oral_extension_has_two_categories_and_eight_distinct_positions():
    categories = {row["extra"]["code"]: row for row in fixture_rows("pose-categories")}
    oral_uid = categories["oral"]["uid"]
    mutual_uid = categories["mutual"]["uid"]
    poses = fixture_rows("poses")
    oral = [row for row in poses if row["category_uid"] == oral_uid]
    mutual = [row for row in poses if row["category_uid"] == mutual_uid]
    assert len(oral) == 6 and len(mutual) == 2
    assert {row["name"] for row in mutual} == {"69 — лёжа", "69 — на боку"}
    for row in oral + mutual:
        assert row["icon"] is row["thumbnail"] is row["url"] is None
        assert row["description"].strip()
        assert row["extra"]["provenance"]["family_sources"]
        assert "modern-64" not in row["extra"].get("collections", [])


def test_oral_extension_preserves_all_previous_records_and_has_frozen_snapshot():
    base = Path(__file__).resolve().parents[2]
    folder = base / "src/vowen/modules/references/fixtures"
    snapshot = json.loads((base / "migrations/fixtures/0049-oral-poses.json").read_text())
    assert len(snapshot["pose-categories"]) == 2 and len(snapshot["poses"]) == 8
    for kind in ("poses", "pose-categories"):
        previous = json.loads((folder / f"v18/{kind}.json").read_text())
        current = json.loads(json.dumps(fixture_rows(kind), default=str))
        assert current[: len(previous) + len(snapshot[kind])] == previous + snapshot[kind]
