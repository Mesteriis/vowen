"""Shared static files remain local and usable by both client packaging layouts."""

import hashlib
import json
from pathlib import Path


def test_static_manifest_resolves_to_regular_project_files_with_original_bytes():
    root = Path(__file__).resolve().parents[3]
    static = root / "static"
    manifest = json.loads((static / "manifest.json").read_text())
    assert manifest["format"] == 1
    assert {"web", "android"} == {Path(p).parts[0] for p in manifest["files"]}
    for relative, digest in manifest["files"].items():
        path = static / relative
        assert not path.is_symlink()
        assert path.resolve().is_relative_to(static.resolve())
        assert path.is_file()
        assert hashlib.sha256(path.read_bytes()).hexdigest() == digest
    images = {".png", ".webp", ".svg", ".jpg", ".jpeg", ".gif", ".avif", ".ico"}
    actual = {str(p.relative_to(static)) for p in static.rglob("*") if p.suffix in images}
    assert actual <= manifest["files"].keys()
    assert not (root / "web/public").exists()
    assert not (root / "android/app/src/main/res/drawable-nodpi").exists()


def test_android_drawable_references_resolve_after_resource_move():
    import re

    root = Path(__file__).resolve().parents[3]
    resources = {p.stem for p in (root / "static/android/res/drawable-nodpi").iterdir()}
    referenced = set()
    for source in (root / "android/app/src/main").rglob("*.kt"):
        referenced.update(re.findall(r"(?<![\w.])R\.drawable\.([A-Za-z0-9_]+)", source.read_text()))
    assert referenced
    assert referenced <= resources
