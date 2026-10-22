import json
from importlib.resources import files
from uuid import UUID

from vowen.modules.references.fixtures import CATALOGUES, fixture_rows


def test_current_reference_counts_links_taxonomy_and_stable_concepts():
    counts = {
        "biological-sex": 3,
        "genders": 7,
        "practices": 93,
        "practice-categories": 13,
        "pose-categories": 14,
        "poses": 106,
        "participant-compositions": 10,
        "devices": 62,
        "body-parts": 23,
        "materials": 15,
        "role-scenarios": 12,
        "interaction-formats": 3,
        "venues": 6,
        "health-conditions": 23,
        "allergens": 16,
        "timezones": 24,
        "relationship-types": 8,
    }
    for kind in CATALOGUES:
        rows = fixture_rows(kind)
        assert len(rows) == counts[kind]
        assert len({row["uid"] for row in rows}) == len(rows)
        assert len({row["name"].casefold() for row in rows}) == len(rows)
        assert all(row["url"] is None and row["description"].strip() for row in rows)
        assert all(row["icon"] is None for row in rows)
        if kind in {"poses", "pose-categories"}:
            assert all(row["thumbnail"] is None for row in rows)
        else:
            assert all(row["thumbnail"].startswith("/references/") for row in rows)
    names = {row["name"] for row in fixture_rows("practices")}
    assert {"Анальный секс", "Вагинальный секс", "Оральный секс", "Мастурбация"} <= names
    assert not {"Активное слушание", "Совместная прогулка", "Уход за обувью"} & names
    original = json.loads(
        files("vowen.modules.references").joinpath("fixtures/v2/practices.json").read_text()
    )
    current = {row["extra"]["code"]: row for row in fixture_rows("practices")}
    for row in original:
        if row["extra"]["code"] in current:
            assert current[row["extra"]["code"]]["uid"] == UUID(row["uid"])


def test_practice_categories_are_foreign_keys_not_description_metadata():
    categories = {row["uid"] for row in fixture_rows("practice-categories")}
    for row in fixture_rows("practices"):
        assert row["category_uid"] in categories
        assert "Категория:" not in row["description"]
        assert "category" not in row["extra"]


def test_practice_aliases_consolidate_variants_without_changing_canonical_uid():
    rows = {row["extra"]["code"]: row for row in fixture_rows("practices")}
    assert "Минет" in rows["fellatio"]["extra"]["aliases"]
    assert "Мастурбация перед зеркалом" in rows["masturbation"]["extra"]["aliases"]
    assert "mirror-masturbation" not in rows
    assert "body-massage" not in rows
    for row in rows.values():
        aliases = row["extra"]["aliases"]
        assert len(aliases) == len(set(aliases))
        assert all(isinstance(alias, str) and alias.strip() for alias in aliases)


def test_compositions_are_independent_of_practices_and_letter_order():
    rows = {row["name"]: row for row in fixture_rows("participant-compositions")}
    assert {"МЖ", "ММ", "ЖЖ", "МЖМ", "ЖМЖ", "МММ", "ЖЖЖ", "ММЖЖ"} <= rows.keys()
    assert rows["МЖМ"]["extra"]["participant_count"] == 3
    assert rows["МЖМ"]["extra"]["men"] == 2
    assert rows["МЖМ"]["extra"]["women"] == 1
    assert "ММЖ" in rows["МЖМ"]["extra"]["aliases"]
    assert "ММЖ" not in rows
    assert "МЖЖ" in rows["ЖМЖ"]["extra"]["aliases"]
    for row in rows.values():
        extra = row["extra"]
        if extra["men"] is not None:
            assert extra["participant_count"] == extra["men"] + extra["women"]
    categories = {row["uid"]: row for row in fixture_rows("practice-categories")}
    practices = {row["name"]: row for row in fixture_rows("practices")}
    for name in ("Секс втроём", "Групповой секс", "Обмен партнёрами", "Свинг"):
        assert categories[practices[name]["category_uid"]]["name"] == "Групповые практики"
    assert not rows.keys() & practices.keys()


def test_equipment_links_reference_existing_records_without_duplicate_pairs():
    from vowen.modules.references.fixtures import link_rows

    practices = {row["uid"] for row in fixture_rows("practices")}
    for kind, field, target in (
        ("practice-devices", "device_uid", "devices"),
        ("practice-body-parts", "body_part_uid", "body-parts"),
    ):
        links = link_rows(kind)
        targets = {row["uid"] for row in fixture_rows(target)}
        assert len({(row["practice_uid"], row[field]) for row in links}) == len(links)
        assert all(row["practice_uid"] in practices and row[field] in targets for row in links)


def test_health_catalogues_are_neutral_terms_without_personal_or_clearance_fields():
    conditions = {row["extra"]["code"]: row for row in fixture_rows("health-conditions")}
    allergens = {row["extra"]["code"]: row for row in fixture_rows("allergens")}
    assert "ПТСР" in conditions["ptsd"]["extra"]["aliases"]
    assert "ВИЧ" in conditions["hiv"]["extra"]["aliases"]
    assert "Натуральный латекс" in allergens["natural-latex"]["extra"]["aliases"]
    assert allergens["natural-latex"]["uid"] != allergens["thiurams"]["uid"]
    assert "silicone" not in allergens
    for row in list(conditions.values()) + list(allergens.values()):
        assert set(row["extra"]) == {"code", "aliases"}
        assert row["url"] is None and row["icon"] is None
        assert "user_id" not in row and "practice_uid" not in row
        assert row["name"] not in {"Здоров", "Без аллергии", "Практика разрешена"}


def test_fixation_and_care_structure_reuses_existing_entries_and_catalogues():
    from vowen.modules.references.fixtures import link_rows

    for kind in CATALOGUES:
        if kind in {"poses", "pose-categories"}:
            continue  # v9 predates the pose catalogues.
        original = json.loads(
            files("vowen.modules.references").joinpath("fixtures/v9", kind + ".json").read_text()
        )
        current_ids = {str(row["uid"]) for row in fixture_rows(kind)}
        original_ids = {row["uid"] for row in original}
        assert original_ids <= current_ids if kind == "devices" else original_ids == current_ids
    devices = {row["extra"]["code"]: row for row in fixture_rows("devices")}
    assert {
        row["name"] for row in devices.values() if row["extra"]["group"] == "Средства фиксации"
    } >= {"Верёвка", "Манжеты"}
    assert devices["collar"]["extra"]["group"] == "Аксессуары динамики"
    assert devices["leash"]["extra"]["group"] == "Аксессуары динамики"
    care = next(
        row for row in fixture_rows("practice-categories") if row["extra"]["code"] == "care"
    )
    assert care["name"] == "Восстановление и забота"
    entries = [row for row in fixture_rows("practices") if row["category_uid"] == care["uid"]]
    assert len(entries) == 3
    assert {row["extra"]["group"] for row in entries} == {"Телесная забота", "После практики"}
    assert len(link_rows("practice-devices")) == 21
    assert len(link_rows("practice-body-parts")) == 11


def test_device_expansion_preserves_v12_and_adds_only_24_stable_device_entries():
    from uuid import uuid5

    namespace = UUID("3e181b46-6a16-4c04-8acb-667ba0fd25a9")
    expected_codes = {
        "linear-sex-machine",
        "rotary-sex-machine",
        "compact-sex-machine",
        "vibrating-saddle",
        "thrusting-vibrator",
        "wand-massager",
        "air-pulse-stimulator",
        "vibrating-ring",
        "masturbator",
        "prostate-massager",
        "double-dildo",
        "suction-cup-dildo",
        "spreader-bar",
        "bondage-straps",
        "bondage-tape",
        "under-bed-restraints",
        "bondage-harness",
        "ankle-cuffs",
        "bondage-cross",
        "bondage-bench",
        "suspension-frame",
        "ball-gag",
        "leather-belt",
        "slapper",
    }
    new = []
    for kind in CATALOGUES:
        if kind in {"poses", "pose-categories"}:
            continue  # These catalogues first appear in v16.
        previous = json.loads(
            files("vowen.modules.references").joinpath("fixtures/v12", kind + ".json").read_text()
        )
        current = json.loads(
            files("vowen.modules.references").joinpath("fixtures/v13", kind + ".json").read_text()
        )
        assert current[: len(previous)] == previous
        if kind == "devices":
            new = current[len(previous) :]
        else:
            assert current == previous
    assert len(new) == 24
    assert {r["extra"]["code"] for r in new} == expected_codes
    assert all(r["uid"] == str(uuid5(namespace, "devices:" + r["extra"]["code"])) for r in new)
    assert {r["extra"]["code"] for r in new if r["extra"]["group"] == "Секс-машины"} == {
        "linear-sex-machine",
        "rotary-sex-machine",
        "compact-sex-machine",
        "vibrating-saddle",
    }
    assert {r["extra"]["code"] for r in new if r["extra"]["discipline_default"]} == {
        "leather-belt",
        "slapper",
    }
    assert all(r["extra"]["aliases"] for r in new)


def test_v14_consolidates_machines_and_adds_eight_toys():
    previous = json.loads(
        files("vowen.modules.references").joinpath("fixtures/v13/devices.json").read_text()
    )
    current = {
        r["extra"]["code"]: {**r, "uid": UUID(r["uid"])}
        for r in json.loads(
            files("vowen.modules.references").joinpath("fixtures/v14/devices.json").read_text()
        )
    }
    assert not {"linear-sex-machine", "rotary-sex-machine", "compact-sex-machine"} & current.keys()
    machine = current["sex-machine"]
    original = next(r for r in previous if r["extra"]["code"] == "linear-sex-machine")
    assert machine["uid"] == UUID(original["uid"])
    assert machine["thumbnail"] == original["thumbnail"]
    assert machine["name"] == "Секс-машина"
    assert "компактная секс-машина" in machine["extra"]["aliases"]
    assert "vibrating-saddle" in current
    assert len(current) == 54
    assert {
        "bullet-vibrator",
        "vibrating-egg",
        "finger-vibrator",
        "couples-vibrator",
        "rabbit-vibrator",
        "flexible-vibrator",
        "vibrating-plug",
        "massage-candle",
    } <= current.keys()
    for row in previous:
        if row["extra"]["code"] not in {
            "linear-sex-machine",
            "rotary-sex-machine",
            "compact-sex-machine",
        }:
            assert {**current[row["extra"]["code"]], "uid": row["uid"]} == row


def test_v15_additions_preserve_v14_and_have_stable_ids():
    from uuid import uuid5

    namespace = UUID("3e181b46-6a16-4c04-8acb-667ba0fd25a9")
    for kind in CATALOGUES:
        if kind in {"poses", "pose-categories"}:
            continue  # These catalogues first appear in v16.
        previous = json.loads(
            files("vowen.modules.references").joinpath("fixtures/v14", kind + ".json").read_text()
        )
        current = json.loads(
            files("vowen.modules.references").joinpath("fixtures/v15", kind + ".json").read_text()
        )
        assert current[: len(previous)] == previous
        if kind != "devices":
            assert current == previous
            continue
        added = current[len(previous) :]
        assert len(added) == 8
        assert {r["extra"]["code"] for r in added} == {
            "glass-stimulator",
            "steel-stimulator",
            "dilator-set",
            "non-vibrating-ring",
            "chastity-belt",
            "positioning-cushion",
            "wedge-cushion",
            "bolster-cushion",
        }
        assert sum(r["extra"]["group"] == "Мебель и опоры" for r in added) == 3
        for row in added:
            assert row["uid"] == str(uuid5(namespace, "devices:" + row["extra"]["code"]))
            assert row["extra"]["discipline_default"] is False
            assert row["extra"]["aliases"]
