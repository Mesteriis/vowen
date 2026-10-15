import importlib.util
import io
import subprocess
import tarfile
from pathlib import Path
from unittest.mock import patch

import pytest

OPS = Path(__file__).parents[1] / "ops"
spec = importlib.util.spec_from_file_location("pull_backup", OPS / "pull_backup.py")
pulling = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pulling)


@pytest.mark.parametrize("failure", ["transport", "unsafe-archive", "bad-repository"])
def test_failed_pull_preserves_previous_generation(tmp_path, monkeypatch, failure):
    monkeypatch.syspath_prepend(str(OPS))
    destination = tmp_path / "backup"
    destination.mkdir(mode=0o700)
    previous = destination / "repo-existing"
    previous.mkdir()
    (previous / "marker").write_text("previous verified generation")
    (destination / "current").symlink_to(previous.name)
    key = tmp_path / "password"
    key.write_text("synthetic fixture")
    key.chmod(0o600)
    content = io.BytesIO()
    with tarfile.open(fileobj=content, mode="w") as archive:
        if failure == "bad-repository":
            item = tarfile.TarInfo("config")
            item.size = 2
            archive.addfile(item, io.BytesIO(b"{}"))
            keys = tarfile.TarInfo("keys")
            keys.type = tarfile.DIRTYPE
            archive.addfile(keys)
        else:
            item = tarfile.TarInfo("outside")
            item.type = tarfile.SYMTYPE
            item.linkname = "/etc/passwd"
            archive.addfile(item)

    def runner(command, **kwargs):
        if command[0] == "ssh":
            kwargs["stdout"].write(content.getvalue())
            return subprocess.CompletedProcess(
                command, 255 if failure == "transport" else 0
            )
        return subprocess.CompletedProcess(command, 1)

    with patch.object(pulling.subprocess, "run", side_effect=runner):
        with pytest.raises((RuntimeError, ValueError)):
            pulling.pull("pve-fixture", "/fixture/repository", destination, key)
    assert (destination / "current").resolve() == previous
    assert (previous / "marker").read_text() == "previous verified generation"
    assert not list(destination.glob("incoming-*"))
