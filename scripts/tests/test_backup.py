import importlib.util
import os
from pathlib import Path
from unittest.mock import patch

import pytest

spec = importlib.util.spec_from_file_location(
    "backup", Path(__file__).parents[1] / "ops/backup.py"
)
backup = importlib.util.module_from_spec(spec)
spec.loader.exec_module(backup)


def test_retention_is_scoped_to_instance_and_never_zero():
    command = backup.retention_command("vowen-ct999", 7, 4, 6)
    assert command[:2] == ["restic", "forget"]
    for flag, value in [
        ("--host", "vowen-ct999"),
        ("--tag", "vowen-app"),
        ("--group-by", "host,tags"),
        ("--keep-last", "3"),
        ("--keep-daily", "7"),
        ("--keep-weekly", "4"),
        ("--keep-monthly", "6"),
    ]:
        assert command[command.index(flag) + 1] == value
    with pytest.raises(ValueError):
        backup.retention_command("vowen-ct999", 0, 4, 6)


def test_credential_rejects_world_readable_and_symlink(tmp_path):
    key = tmp_path / "password"
    key.write_text("synthetic backup password")
    key.chmod(0o644)
    with pytest.raises(ValueError):
        backup.private_file(key)
    key.chmod(0o600)
    backup.private_file(key)
    link = tmp_path / "link"
    link.symlink_to(key)
    with pytest.raises(ValueError):
        backup.private_file(link)


def test_capture_failure_never_calls_restic_or_retention(tmp_path):
    key = tmp_path / "key"
    key.write_text("synthetic")
    key.chmod(0o600)
    repository = tmp_path / "repo"
    repository.mkdir(mode=0o700)
    (repository / "config").write_text("{}")
    with (
        patch.dict(
            os.environ, RESTIC_PASSWORD_FILE=str(key), RESTIC_REPOSITORY=str(repository)
        ),
        patch.object(backup, "capture", side_effect=RuntimeError("fixture failure")),
        patch.object(backup, "run") as runner,
    ):
        with pytest.raises(RuntimeError):
            backup.perform(999, tmp_path / "work", 7, 4, 6)
        runner.assert_not_called()
    assert not list((tmp_path / "work").iterdir())


@pytest.mark.parametrize("failure", ["backup", "check", "dump", "restore-mismatch"])
def test_unverified_backup_never_prunes(tmp_path, failure):
    import subprocess

    key = tmp_path / "key"
    key.write_text("fixture")
    key.chmod(0o600)
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "config").write_text("{}")
    calls = []

    def capture_fixture(ctid, target):
        target.write_bytes(b"synthetic captured data")

    def command_fixture(command, **kwargs):
        calls.append(command)
        if command[1] == failure:
            raise RuntimeError("fixture failed stage")
        if command[1] == "dump":
            kwargs["stdout"].write(
                b"wrong"
                if failure == "restore-mismatch"
                else b"synthetic captured data"
            )
        return subprocess.CompletedProcess(
            command, 0, b'{"message_type":"summary","snapshot_id":"fixture"}\n'
        )

    with (
        patch.dict(
            os.environ, RESTIC_PASSWORD_FILE=str(key), RESTIC_REPOSITORY=str(repo)
        ),
        patch.object(backup, "capture", side_effect=capture_fixture),
        patch.object(backup, "run", side_effect=command_fixture),
    ):
        with pytest.raises(RuntimeError):
            backup.perform(999, tmp_path / "work", 7, 4, 6)
    assert not any(command[1] == "forget" for command in calls)
    assert not list((tmp_path / "work").iterdir())


def test_real_restic_roundtrip_wrong_key_and_scoped_retention(tmp_path):
    import shutil
    import subprocess

    if not shutil.which("restic"):
        pytest.fail("Install restic to run the backup acceptance test")
    repo, key = tmp_path / "repo", tmp_path / "password"
    key.write_text("synthetic-only-fixture-password")
    key.chmod(0o600)
    environment = dict(
        os.environ, RESTIC_REPOSITORY=str(repo), RESTIC_PASSWORD_FILE=str(key)
    )
    subprocess.run(["restic", "init"], env=environment, check=True, capture_output=True)
    # An unrelated backup set must survive our retention operation.
    subprocess.run(
        [
            "restic",
            "backup",
            "--stdin",
            "--stdin-filename",
            "unrelated",
            "--host",
            "unrelated",
            "--tag",
            "other",
        ],
        input=b"other fixture",
        env=environment,
        check=True,
        capture_output=True,
    )
    with (
        patch.dict(os.environ, environment),
        patch.object(
            backup,
            "capture",
            side_effect=lambda c, p: p.write_bytes(b"fixture tar bytes"),
        ),
    ):
        snapshot_id = backup.perform(999, tmp_path / "work", 7, 4, 6)
    restored = subprocess.run(
        ["restic", "dump", snapshot_id, "snapshot.tar"],
        env=environment,
        check=True,
        capture_output=True,
    )
    assert restored.stdout == b"fixture tar bytes"
    snapshots = subprocess.run(
        ["restic", "snapshots", "--json"],
        env=environment,
        check=True,
        capture_output=True,
    )
    import json

    assert {item["hostname"] for item in json.loads(snapshots.stdout)} == {
        "unrelated",
        "vowen-ct999",
    }
    key.write_text("wrong-fixture-password")
    rejected = subprocess.run(
        ["restic", "dump", snapshot_id, "snapshot.tar"],
        env=environment,
        check=False,
        capture_output=True,
    )
    assert rejected.returncode != 0
    assert not rejected.stdout
