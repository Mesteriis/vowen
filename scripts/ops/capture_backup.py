"""Guest-side online PostgreSQL snapshot with stable source/keyring/configuration."""

import argparse
import hashlib
import json
import os
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path

EXCLUDE = {
    ".git",
    ".serena",
    ".superpowers",
    ".venv",
    "node_modules",
    "build",
    ".gradle",
    ".kotlin",
    "artifacts",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    "dist",
    "secrets",
    ".env",
    ".DS_Store",
    "local.properties",
}


def files(root: Path) -> list[Path]:
    result = []
    for directory, dirs, names in os.walk(root, followlinks=False):
        dirs[:] = sorted(name for name in dirs if name not in EXCLUDE)
        if any((Path(directory) / name).is_symlink() for name in dirs):
            raise ValueError("Source contains a directory symlink")
        for name in sorted(names):
            path = Path(directory) / name
            if (
                name in EXCLUDE
                or name.startswith(".env.")
                or name.endswith((".jks", ".keystore", ".pyc"))
            ):
                continue
            if path.is_symlink() or not path.is_file():
                raise ValueError("Source contains a non-regular file")
            result.append(path)
    return result


def fingerprint(paths: list[Path], root: Path) -> dict[str, str]:
    result = {}
    for path in paths:
        if path.is_symlink() or not path.is_file():
            raise ValueError("Refusing a symlink or non-regular configuration file")
        with path.open("rb") as stream:
            result[str(path.relative_to(root))] = hashlib.file_digest(
                stream, "sha256"
            ).hexdigest()
    return result


def execute(command, **kwargs):
    result = subprocess.run(command, check=False, stderr=subprocess.PIPE, **kwargs)
    if result.returncode:
        raise RuntimeError("Guest capture command failed")
    return result


def capture(root: Path, destination) -> None:
    os.umask(0o077)
    source = files(root)
    required = [
        root / ".env",
        root / "secrets/keyring.json",
        root / "secrets/bot-token",
        root / ".deployed-revision",
    ]
    before = fingerprint(source + required, root)
    compose = [
        "docker",
        "compose",
        "-f",
        str(root / "compose.yaml"),
        "-f",
        str(root / "deploy/pve/compose.edge.yaml"),
        "--profile",
        "telegram",
    ]
    with tempfile.TemporaryDirectory(prefix="vowen-capture-", dir="/run") as work:
        work = Path(work)
        with (work / "database.dump").open("xb") as stream:
            execute(
                compose
                + ["exec", "-T", "db", "pg_dump", "-U", "vowen", "-d", "vowen", "-Fc"],
                stdout=stream,
            )
        with (work / "database.dump").open("rb") as stream:
            execute(
                compose + ["exec", "-T", "db", "pg_restore", "--list"],
                stdin=stream,
                stdout=subprocess.DEVNULL,
            )
        schema = (
            execute(
                compose
                + [
                    "exec",
                    "-T",
                    "db",
                    "psql",
                    "-U",
                    "vowen",
                    "-d",
                    "vowen",
                    "-Atc",
                    "SELECT version_num FROM alembic_version",
                ],
                stdout=subprocess.PIPE,
            )
            .stdout.decode()
            .strip()
        )
        for filename, selected in [
            ("source.tar.gz", source),
            ("secrets-config.tar.gz", required[:3]),
        ]:
            with tarfile.open(work / filename, "w:gz") as archive:
                for path in selected:
                    archive.add(
                        path, arcname=str(path.relative_to(root)), recursive=False
                    )
        if before != fingerprint(files(root) + required, root):
            raise RuntimeError(
                "Source or secrets changed during backup; capture rejected"
            )
        manifest = {
            "format": 1,
            "revision": (root / ".deployed-revision").read_text().strip(),
            "schema": schema,
            "sha256": fingerprint(list(work.iterdir()), work),
            "consistency": "online pg_dump transaction; immutable source/config fingerprints",
        }
        (work / "manifest.json").write_text(json.dumps(manifest, sort_keys=True) + "\n")
        with tarfile.open(fileobj=destination, mode="w|") as archive:
            for path in sorted(work.iterdir()):
                archive.add(path, arcname=path.name, recursive=False)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    args = parser.parse_args()
    try:
        capture(args.root.resolve(strict=True), sys.stdout.buffer)
    except (RuntimeError, ValueError, OSError):
        raise SystemExit("Capture failed; no backup accepted") from None
