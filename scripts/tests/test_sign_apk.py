import importlib.util
import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest

spec = importlib.util.spec_from_file_location(
    "sign_apk", Path(__file__).parents[1] / "sign_apk.py"
)
signing = importlib.util.module_from_spec(spec)
spec.loader.exec_module(signing)


def test_signer_uses_one_password_file_and_verifies_before_metadata(
    tmp_path, monkeypatch
):
    key, password = tmp_path / "fixture.keystore", tmp_path / "password"
    for file in (key, password):
        file.write_text("synthetic fixture")
        file.chmod(0o600)
    unsigned, output = tmp_path / "unsigned.apk", tmp_path / "signed.apk"
    unsigned.write_bytes(b"fixture apk")
    monkeypatch.setenv("ANDROID_HOME", "/synthetic/sdk")
    monkeypatch.setattr(
        "sys.argv",
        [
            "sign_apk",
            "--unsigned",
            str(unsigned),
            "--output",
            str(output),
            "--keystore",
            str(key),
            "--password-file",
            str(password),
        ],
    )
    calls = []

    def runner(command, **kwargs):
        calls.append(command)
        if command[1] == "sign":
            # apksigner consumes consecutive lines if the same file is specified twice.
            assert command.count("file:" + str(password)) == 1
            assert password.read_text() not in " ".join(command)
            Path(command[command.index("--out") + 1]).write_bytes(b"signed fixture")
        else:
            assert not output.with_suffix(".json").exists()
        return subprocess.CompletedProcess(
            command,
            0,
            "Signer #1 certificate SHA-256 digest: fixture-public-certificate\n",
        )

    with patch.object(signing.subprocess, "run", side_effect=runner):
        signing.main()
    assert [c[1] for c in calls] == ["sign", "verify"]
    assert output.with_suffix(".json").is_file()
    assert unsigned.read_bytes() == b"fixture apk"


def test_signing_rejects_permissive_password(tmp_path):
    key = tmp_path / "password"
    key.write_text("synthetic")
    key.chmod(0o644)
    with pytest.raises(ValueError):
        signing.private_file(key)
