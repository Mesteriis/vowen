"""Versioned generated fixture paths resolve to immutable audited transparent PNG assets."""

import hashlib
import json
import struct
from importlib.resources import files
from pathlib import Path

from vowen.modules.references.fixtures import CATALOGUES


def test_all_reference_thumbnails_are_real_audited_assets_and_preserve_existing_assets():
    root = Path(__file__).resolve().parents[3]
    measured = {
        row["uid"]: row
        for row in json.loads((root / "scripts/fixtures/reference-thumbnails-v15.json").read_text())
    }
    assert len(measured) == 318
    seen_hashes = set()
    seen_uids = set()
    for kind in CATALOGUES:
        current = json.loads(
            files("vowen.modules.references").joinpath("fixtures/v15", kind + ".json").read_text()
        )
        previous = json.loads(
            files("vowen.modules.references").joinpath("fixtures/v14", kind + ".json").read_text()
        )
        assert current[: len(previous)] == previous
        assert len(current) == len(previous) + (8 if kind == "devices" else 0)
        for row in current:
            assert row["icon"] is None and row["url"] is None
            assert row["thumbnail"].startswith("/references/" + kind + "/")
            asset = root / "static/web" / row["thumbnail"].lstrip("/")
            assert asset.resolve().is_relative_to((root / "static/web/references").resolve())
            content = asset.read_bytes()
            assert content[:8] == b"\x89PNG\r\n\x1a\n"
            width, height, depth, mode, _, _, _ = struct.unpack(">IIBBBBB", content[16:29])
            assert width == height and depth == 8 and mode == 6
            digest = hashlib.sha256(content).hexdigest()
            assert digest not in seen_hashes
            seen_hashes.add(digest)
            seen_uids.add(row["uid"])
            report = measured[row["uid"]]
            assert report["sha256"] == digest and report["thumbnail"] == row["thumbnail"]
            assert report["fully_transparent_fraction"] > 0.05
    assert len(seen_hashes) == 318
    assert seen_uids == set(measured)
