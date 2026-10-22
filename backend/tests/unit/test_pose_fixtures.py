from uuid import UUID, uuid5

from vowen.modules.references.fixtures import fixture_rows


def test_pose_fixtures_have_stable_ids_and_explicit_categories():
    namespace = UUID("3e181b46-6a16-4c04-8acb-667ba0fd25a9")
    categories = fixture_rows("pose-categories")
    poses = fixture_rows("poses")
    assert len(categories) == 14
    assert len(poses) == 106
    category_ids = {row["uid"] for row in categories}
    assert {row["category_uid"] for row in poses} == category_ids
    for kind, rows in [("pose-categories", categories), ("poses", poses)]:
        assert len({row["uid"] for row in rows}) == len(rows)
        assert len({row["name"].casefold() for row in rows}) == len(rows)
        for row in rows:
            assert row["uid"] == uuid5(namespace, kind + ":" + row["extra"]["code"])
            assert row["name"].strip() and row["description"].strip()
            assert row["icon"] is row["thumbnail"] is row["url"] is None
            assert "category" not in row["extra"]
    assert {"Миссионерская", "Наездница", "Ложки", "Лотос", "Наду"} <= {
        row["name"] for row in poses
    }


def test_pose_migration_snapshot_matches_the_initial_fixtures():
    import json
    from pathlib import Path

    snapshot = json.loads(
        (Path(__file__).resolve().parents[2] / "migrations/fixtures/0046-poses.json").read_text()
    )
    for kind in ["poses", "pose-categories"]:
        normalized = json.loads(json.dumps(fixture_rows(kind), default=str))
        initial = normalized[: len(snapshot[kind])]
        if kind == "poses":
            for row in initial:
                row["extra"].pop("collections", None)
        assert snapshot[kind] == initial
