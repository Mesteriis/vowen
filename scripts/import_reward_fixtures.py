"""Import synthetic marketplace examples through the local development API.

Never resets data, wallets or grants. Existing listings are preserved by default.
Explicit --sync-categories publishes category-only revisions, preserving current content.
Run serially as a canonical dominant; existing products match across the catalogue.
"""

import argparse
import json
import struct
from pathlib import Path
from urllib.parse import urlsplit

import httpx
from vowen.modules.rewards.schemas import RewardContent

FIXTURES = Path(__file__).parent / "fixtures" / "rewards.json"


def validate_fixture_assets() -> None:
    root = Path(__file__).resolve().parents[1]
    for item in json.loads(FIXTURES.read_text()):
        content = RewardContent.model_validate(
            {
                key: value
                for key, value in item.items()
                if key not in {"price", "audience_all"}
            }
        )
        path = root / "static/web/shop" / f"{content.cover}.png"
        with path.open("rb") as image:
            header = image.read(24)
        if header[:8] != b"\x89PNG\r\n\x1a\n" or header[12:16] != b"IHDR":
            raise ValueError(f"Invalid fixture image: {content.cover}")
        if min(struct.unpack(">II", header[16:24])) < 256:
            raise ValueError(f"Fixture image is too small: {content.cover}")


def import_rewards(
    client: httpx.Client,
    author_name: str,
    recipient_name: str,
    *,
    sync_categories: bool = False,
) -> dict[str, int]:
    if not all(name.endswith(" · демо") for name in (author_name, recipient_name)):
        raise ValueError(
            "Only explicitly named synthetic demo participants are supported"
        )

    def call(method: str, path: str, body: dict | None = None):
        response = client.request(method, path, json=body)
        # Do not include response payloads or authorization material in errors/logs.
        if response.is_error:
            raise RuntimeError(
                f"Local fixture API failed: {method} {path}: {response.status_code}"
            )
        return response.json()

    # DEBUG endpoints are unavailable outside explicitly enabled development mode.
    users = call("GET", "auth/debug/users")

    def user_id(name: str) -> str:
        matches = [u["id"] for u in users if u["display_name"] == name]
        if len(matches) != 1:
            raise ValueError("Expected exactly one matching synthetic participant")
        return matches[0]

    author, recipient = user_id(author_name), user_id(recipient_name)
    tokens = call("POST", "auth/debug", {"user_id": author})
    client.headers["Authorization"] = "Bearer " + tokens["access_token"]
    if call("GET", "me")["shop_role"] != "dominant":
        raise ValueError("Fixture import requires a canonical dominant shop role")
    # Resolve the explicitly named recipient, but public products need no relationship.
    del recipient
    # Validate the entire file before creating anything.
    fixtures = json.loads(FIXTURES.read_text())
    contents = []
    for item in fixtures:
        price = item["price"]
        if type(price) is not int or not 1 <= price <= 1_000_000_000:
            raise ValueError("Invalid fixture price")
        if type(item.get("audience_all", False)) is not bool:
            raise ValueError("Invalid fixture audience")
        contents.append(
            (
                RewardContent.model_validate(
                    {
                        key: value
                        for key, value in item.items()
                        if key not in {"price", "audience_all"}
                    }
                ).model_dump(),
                price,
                item.get("audience_all", False),
            )
        )
    if len({content["title"] for content, _, _ in contents}) != len(contents):
        raise ValueError("Duplicate fixture titles")
    listings = call("GET", "shop/catalogue")
    counts = {"definitions_added": 0, "listings_added": 0, "listings_preserved": 0}
    if sync_categories:
        counts["categories_updated"] = 0
    for content, price, everyone in contents:
        matches = [
            row
            for row in listings
            if row["title"] in {content["title"], content["title"] + " · демо"}
        ]
        if len(matches) > 1:
            raise ValueError("Ambiguous existing fixture product title")
        if matches:
            current = matches[0]
            if sync_categories and current.get("category") != content["category"]:
                call(
                    "PATCH",
                    f"shop/products/{current['product_id']}",
                    {
                        **{
                            key: current[key]
                            for key in (
                                "title",
                                "description",
                                "conditions",
                                "cover",
                                "price",
                                "audience_all",
                            )
                        },
                        "category": content["category"],
                        "expected_version": current["product_revision"],
                    },
                )
                counts["categories_updated"] += 1
            counts["listings_preserved"] += 1
            continue
        created = call(
            "POST",
            "shop/products",
            {
                **content,
                "price": price,
                "audience_all": everyone,
            },
        )
        listings.append(created)
        counts["definitions_added"] += 1
        counts["listings_added"] += 1
    return counts


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--api", default="http://127.0.0.1:8002/api/v1/")
    parser.add_argument("--origin", default="http://127.0.0.1:5176")
    parser.add_argument("--author", default="Саша · демо")
    parser.add_argument("--recipient", default="Алекс · демо")
    parser.add_argument("--sync-categories", action="store_true")
    args = parser.parse_args()
    validate_fixture_assets()
    origin = urlsplit(args.origin)
    if (
        origin.scheme != "http"
        or origin.hostname not in {"127.0.0.1", "localhost", "::1"}
        or origin.username
        or origin.password
        or origin.path
        or origin.query
        or origin.fragment
    ):
        parser.error("Only a loopback development origin is allowed")
    url = urlsplit(args.api)
    if (
        url.scheme != "http"
        or url.hostname not in {"127.0.0.1", "localhost", "::1"}
        or url.username
        or url.password
        or url.query
        or url.fragment
    ):
        parser.error("Only a loopback HTTP development API is allowed")
    with httpx.Client(
        base_url=args.api.rstrip("/") + "/",
        timeout=20,
        trust_env=False,
        follow_redirects=False,
        headers={"Origin": args.origin},
    ) as client:
        print(
            json.dumps(
                import_rewards(
                    client,
                    args.author,
                    args.recipient,
                    sync_categories=args.sync_categories,
                )
            )
        )


if __name__ == "__main__":
    main()
