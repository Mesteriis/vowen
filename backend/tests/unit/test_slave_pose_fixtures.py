import json
from pathlib import Path
from uuid import UUID

from vowen.modules.references.fixtures import fixture_rows


def test_slave_pose_category_covers_all_seventeen_reference_files_without_images():
    categories = fixture_rows("pose-categories")
    category = next(row for row in categories if row["name"] == "Позы рабыни")
    poses = [row for row in fixture_rows("poses") if row["category_uid"] == category["uid"]]
    expected = {f"IMG_{n:04d}.PNG" for n in [*range(12, 24), 25, 26, 27, 28, 30]}
    assert len(poses) == 17
    assert {row["extra"]["source_file"] for row in poses} == expected
    assert len({row["name"] for row in poses}) == 17
    assert all(len(row["description"]) >= 250 for row in poses)
    assert all(row["icon"] is row["thumbnail"] is row["url"] is None for row in poses)
    assert all(row["extra"]["group"] for row in poses)
    assert all("/Users/" not in json.dumps(row, default=str) for row in poses)


def test_slave_pose_migration_freezes_only_the_new_records():
    snapshot = json.loads(
        (
            Path(__file__).resolve().parents[2] / "migrations/fixtures/0047-slave-poses.json"
        ).read_text()
    )
    assert len(snapshot["pose-categories"]) == 1
    assert len(snapshot["poses"]) == 17
    category = snapshot["pose-categories"][0]
    for kind in ["pose-categories", "poses"]:
        current = [
            row
            for row in fixture_rows(kind)
            if row.get("category_uid", row["uid"]) == UUID(category["uid"])
        ]
        assert snapshot[kind] == json.loads(json.dumps(current, default=str))


def test_researched_terms_are_distinguished_from_unconfirmed_names():
    poses = [row for row in fixture_rows("poses") if "source_file" in row["extra"]]
    researched = [row for row in poses if row["extra"]["terminology"]["match"] == "variant"]
    assert len(researched) == 4
    for row in poses:
        extra = row["extra"]
        terminology = extra["terminology"]
        if terminology["match"] == "variant":
            assert terminology["name"] and terminology["sources"] and extra["purpose"]
            assert all(url.startswith("https://") for url in terminology["sources"])
        else:
            assert terminology["match"] == "descriptive"
            assert terminology["name"] is None and extra["purpose"] is None
            assert terminology["sources"] == []
