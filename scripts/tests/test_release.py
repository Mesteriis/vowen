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
