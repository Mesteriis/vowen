import importlib.util
import tarfile
from pathlib import Path

MODULE = Path(__file__).parents[1] / "release.py"
spec = importlib.util.spec_from_file_location("release", MODULE)
release = importlib.util.module_from_spec(spec)
spec.loader.exec_module(release)


def test_archive_is_reproducible_and_normalizes_metadata(tmp_path):
    tree = tmp_path / "tree"
    tree.mkdir()
    (tree / "index.html").write_text("public fixture")
    one, two = tmp_path / "one.tar.gz", tmp_path / "two.tar.gz"
    release.archive_tree(tree, one, 1234567890)
    (tree / "index.html").touch()
    release.archive_tree(tree, two, 1234567890)
    assert one.read_bytes() == two.read_bytes()
    with tarfile.open(one) as archive:
        item = archive.getmember("index.html")
        assert item.uid == item.gid == 0
        assert item.mtime == 1234567890


def test_archive_rejects_symlink(tmp_path):
    tree = tmp_path / "tree"
    tree.mkdir()
    (tree / "link").symlink_to("/etc/passwd")
    import pytest

    with pytest.raises(ValueError):
        release.archive_tree(tree, tmp_path / "out.tar.gz", 1234567890)


def test_normalize_install_removes_only_cache_metadata_and_updates_record(tmp_path):
    import csv

    normalize_spec = importlib.util.spec_from_file_location(
        "normalize_install", MODULE.parent / "normalize_install.py"
    )
    module = importlib.util.module_from_spec(normalize_spec)
    normalize_spec.loader.exec_module(module)
    dist = tmp_path / "fixture-1.dist-info"
    dist.mkdir()
    (dist / "uv_cache.json").write_text('{"timestamp":"variable fixture"}')
    metadata = dist / "METADATA"
    metadata.write_bytes(b"public package metadata")
    rows = [
        ["fixture-1.dist-info/uv_cache.json", "variable-hash", "42"],
        ["fixture-1.dist-info/METADATA", "unchanged-hash", "23"],
    ]
    with (dist / "RECORD").open("w", newline="") as stream:
        csv.writer(stream).writerows(rows)
    module.normalize(tmp_path)
    assert not (dist / "uv_cache.json").exists()
    assert metadata.read_bytes() == b"public package metadata"
    with (dist / "RECORD").open(newline="") as stream:
        assert list(csv.reader(stream)) == rows[1:]
