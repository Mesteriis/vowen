import json
from importlib.resources import files
from pathlib import Path
from uuid import UUID

from vowen.modules.references.fixtures import fixture_rows


def test_modern_selection_has_64_unique_records_and_reuses_existing_ids():
    folder = files("vowen.modules.references").joinpath("fixtures/v18")
    selection = json.loads(folder.joinpath("modern-selection.json").read_text())
    poses = fixture_rows("poses")
    selected = [row for row in poses if "modern-64" in row["extra"].get("collections", [])]
    assert selection["kind"] == "modern_editorial_selection"
    assert selection["historical_attribution"] is None
    assert len(selected) == len(selection["pose_uids"]) == 64
    assert len(set(selection["pose_uids"])) == 64
    assert {str(row["uid"]) for row in selected} == set(selection["pose_uids"])
    old = json.loads(folder.parent.joinpath("v17/poses.json").read_text())
    old_ids = {UUID(row["uid"]) for row in old}
    assert len(old_ids & {row["uid"] for row in selected}) == 21
    assert len(poses) == 106
    current = {str(row["uid"]): json.loads(json.dumps(row, default=str)) for row in poses}
    for previous in old:
        actual = current[previous["uid"]]
        actual["extra"].pop("collections", None)
        assert actual == previous
    assert all(row["icon"] is row["thumbnail"] is row["url"] is None for row in selected)
    assert all(row["description"].strip() for row in selected)
    assert all("source_file" not in row["extra"] for row in selected)


def test_modern_selection_migration_snapshot_preserves_prior_fixtures():
    snapshot = json.loads(
        (
            Path(__file__).resolve().parents[2] / "migrations/fixtures/0048-modern-poses.json"
        ).read_text()
    )
    assert len(snapshot["poses"]) == 43
    assert len(snapshot["existing_pose_uids"]) == 21
    current = {str(row["uid"]): row for row in fixture_rows("poses")}
    assert all(
        current[uid]["extra"]["collections"] == ["modern-64"]
        for uid in snapshot["existing_pose_uids"]
    )
    for row in snapshot["poses"]:
        assert row == json.loads(json.dumps(current[row["uid"]], default=str))
        provenance = row["extra"]["provenance"]
        assert provenance["kind"] == "editorial_variant"
        assert provenance["source_scope"] == "family_only"
        assert provenance["family_sources"]
