import importlib.util
import json
from pathlib import Path

import httpx
import pytest
from pydantic import ValidationError

from vowen.modules.rewards.schemas import RewardContent


def test_all_103_reward_fixtures_have_complete_unique_content():
    root = Path(__file__).resolve().parents[3]
    fixtures = json.loads((root / "scripts/fixtures/rewards.json").read_text())
    assert len(fixtures) == 103
    assert len({item["category"] for item in fixtures}) == 12
    assert len({item["title"] for item in fixtures}) == 103
    assert len({item["cover"] for item in fixtures}) == 103
    for item in fixtures:
        assert set(item) == {
            "title",
            "description",
            "conditions",
            "cover",
            "category",
            "price",
            "audience_all",
        }
        assert type(item["price"]) is int and 1 <= item["price"] <= 1_000_000_000
        assert item["audience_all"] is True
        assert "демо" not in item["title"].lower()
        assert len(item["description"]) > 20 and len(item["conditions"]) > 20
        RewardContent.model_validate(
            {key: value for key, value in item.items() if key not in {"price", "audience_all"}}
        )


@pytest.mark.parametrize(
    "cover",
    [
        "../reward-005",
        "https://host/reward-005",
        "reward-104",
        "reward-000",
        "reward-005.png",
        "reward-005/extra",
    ],
)
def test_reward_cover_rejects_paths_urls_and_unknown_assets(cover):
    with pytest.raises(ValidationError):
        RewardContent(title="Reward", description="Description", cover=cover)


def test_reward_fixture_import_is_repeatable_and_preserves_existing_listing():
    root = Path(__file__).resolve().parents[3]
    spec = importlib.util.spec_from_file_location(
        "reward_fixtures", root / "scripts/import_reward_fixtures.py"
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    fixtures = json.loads(module.FIXTURES.read_text())
    listings = [{"title": fixtures[0]["title"], "price": 17, "active": False}]
    original = dict(listings[0])
    mutations = []

    def handle(request):
        path = request.url.path.removeprefix("/api/v1/")
        if request.method == "GET":
            data = {
                "auth/debug/users": [
                    {"id": "author", "display_name": "Саша · демо"},
                    {"id": "recipient", "display_name": "Алекс · демо"},
                ],
                "me": {"shop_role": "dominant"},
                "shop/catalogue": listings,
            }[path]
        elif path == "auth/debug":
            data = {"access_token": "synthetic"}
        elif path == "shop/products":
            mutations.append(path)
            data = {**json.loads(request.content), "id": str(len(listings)), "active": True}
            listings.append(data)
        else:
            raise AssertionError(f"Unexpected mutation: {path}")
        return httpx.Response(200, json=data)

    with httpx.Client(
        base_url="http://127.0.0.1/api/v1/", transport=httpx.MockTransport(handle)
    ) as client:
        first = module.import_rewards(client, "Саша · демо", "Алекс · демо")
        second = module.import_rewards(client, "Саша · демо", "Алекс · демо")
    assert first == {
        "definitions_added": len(fixtures) - 1,
        "listings_added": len(fixtures) - 1,
        "listings_preserved": 1,
    }
    assert second == {
        "definitions_added": 0,
        "listings_added": 0,
        "listings_preserved": len(fixtures),
    }
    assert len(mutations) == len(fixtures) - 1
    assert listings[0] == original


def test_category_sync_preserves_edited_content_price_and_audience():
    root = Path(__file__).resolve().parents[3]
    spec = importlib.util.spec_from_file_location(
        "reward_category_sync", root / "scripts/import_reward_fixtures.py"
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    fixtures = json.loads(module.FIXTURES.read_text())
    listings = [dict(row, product_id=str(i), product_revision=3) for i, row in enumerate(fixtures)]
    listings[0].update(
        description="Edited description",
        price=17,
        audience_all=False,
        category="together",
        active=False,
        global_enabled=False,
    )
    original = dict(listings[0])
    patches = []

    def handle(request):
        path = request.url.path.removeprefix("/api/v1/")
        if request.method == "GET":
            data = {
                "auth/debug/users": [
                    {"id": "author", "display_name": "Саша · демо"},
                    {"id": "recipient", "display_name": "Алекс · демо"},
                ],
                "me": {"shop_role": "dominant"},
                "shop/catalogue": listings,
            }[path]
        elif path == "auth/debug":
            data = {"access_token": "synthetic"}
        elif request.method == "PATCH" and path == "shop/products/0":
            body = json.loads(request.content)
            patches.append(body)
            assert body["expected_version"] == 3
            listings[0].update({k: v for k, v in body.items() if k != "expected_version"})
            listings[0]["product_revision"] += 1
            data = listings[0]
        else:
            raise AssertionError("Unexpected mutation")
        return httpx.Response(200, json=data)

    with httpx.Client(
        base_url="http://127.0.0.1/api/v1/", transport=httpx.MockTransport(handle)
    ) as client:
        first = module.import_rewards(client, "Саша · демо", "Алекс · демо", sync_categories=True)
        second = module.import_rewards(client, "Саша · демо", "Алекс · демо", sync_categories=True)
    assert first["categories_updated"] == 1
    assert second["categories_updated"] == 0
    assert len(patches) == 1
    assert listings[0] == {**original, "category": fixtures[0]["category"], "product_revision": 4}
