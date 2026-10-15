"""PVE-side encrypted application backup; capture, verify, then scoped retention."""

import argparse
import fcntl
import hashlib
import json
import os
import stat
import subprocess
import tempfile
from pathlib import Path

TAG = "vowen-app"


def private_file(path: Path) -> None:
    mode = path.lstat()
    if (
        not stat.S_ISREG(mode.st_mode)
        or mode.st_uid != os.getuid()
        or mode.st_mode & 0o077
    ):
        raise ValueError(
            "Credential must be a regular owner-only file owned by this user"
        )


def run(command, **kwargs):
    # Subprocess stderr may include credentials/configuration. Report only the failed stage.
    result = subprocess.run(command, check=False, stderr=subprocess.PIPE, **kwargs)
    if result.returncode:
        raise RuntimeError(
            f"Backup stage failed: {command[0]} {command[1]} (exit {result.returncode})"
        )
    return result


def retention_command(host: str, daily: int, weekly: int, monthly: int) -> list[str]:
    if min(daily, weekly, monthly) < 1:
        raise ValueError("Retention counts must be positive")
    return [
        "restic",
        "forget",
        "--host",
        host,
        "--tag",
        TAG,
        "--group-by",
        "host,tags",
        "--keep-last",
        "3",
        "--keep-daily",
        str(daily),
        "--keep-weekly",
        str(weekly),
        "--keep-monthly",
        str(monthly),
        "--prune",
    ]


def capture(ctid: int, target: Path) -> None:
    with target.open("xb") as stream:
        run(
            [
                "pct",
                "exec",
                str(ctid),
                "--",
                "python3",
                "/usr/local/lib/vowen/capture_backup.py",
                "--root",
                "/opt/vowen",
            ],
            stdout=stream,
        )
    import tarfile

    with tarfile.open(target) as archive:
        for required in (
            "manifest.json",
            "database.dump",
            "source.tar.gz",
            "secrets-config.tar.gz",
        ):
            archive.getmember(required)


def sha256(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def perform(ctid: int, workspace: Path, daily: int, weekly: int, monthly: int) -> str:
    os.umask(0o077)
    retention = retention_command(f"vowen-ct{ctid}", daily, weekly, monthly)
    private_file(Path(os.environ["RESTIC_PASSWORD_FILE"]))
    repository = Path(os.environ["RESTIC_REPOSITORY"])
    if (
        not repository.is_absolute()
        or repository.is_symlink()
        or not (repository / "config").is_file()
    ):
        raise ValueError(
            "Initialize a dedicated local restic repository explicitly first"
        )
    workspace.mkdir(mode=0o700, parents=True, exist_ok=True)
    if (
        workspace.is_symlink()
        or workspace.stat().st_uid != os.getuid()
        or workspace.stat().st_mode & 0o077
    ):
        raise ValueError("Backup workspace must be an owner-only real directory")
    with tempfile.TemporaryDirectory(prefix="capture-", dir=workspace) as temporary:
        snapshot = Path(temporary) / "snapshot.tar"
        capture(ctid, snapshot)
        with snapshot.open("rb") as stream:
            result = run(
                [
                    "restic",
                    "backup",
                    "--stdin",
                    "--stdin-filename",
                    "snapshot.tar",
                    "--host",
                    f"vowen-ct{ctid}",
                    "--tag",
                    TAG,
                    "--json",
                ],
                stdin=stream,
                stdout=subprocess.PIPE,
            )
        summaries = [json.loads(line) for line in result.stdout.splitlines()]
        snapshot_id = next(
            item["snapshot_id"]
            for item in summaries
            if item.get("message_type") == "summary"
        )
        run(["restic", "check"], stdout=subprocess.DEVNULL)
        restored = Path(temporary) / "restored.tar"
        with restored.open("xb") as stream:
            run(["restic", "dump", snapshot_id, "snapshot.tar"], stdout=stream)
        if sha256(snapshot) != sha256(restored):
            raise RuntimeError(
                "Authenticated restore differs from captured backup; retention skipped"
            )
        run(retention, stdout=subprocess.DEVNULL)
        run(["restic", "check"], stdout=subprocess.DEVNULL)
        return snapshot_id


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ctid", type=int, required=True)
    parser.add_argument("--workspace", type=Path, default=Path("/run/vowen-backup"))
    parser.add_argument(
        "--lock", type=Path, default=Path("/run/lock/vowen-backup.lock")
    )
    parser.add_argument("--daily", type=int, default=7)
    parser.add_argument("--weekly", type=int, default=4)
    parser.add_argument("--monthly", type=int, default=6)
    args = parser.parse_args()
    if args.ctid < 100:
        parser.error("Expected a PVE guest ID >= 100")
    os.umask(0o077)
    with args.lock.open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        snapshot_id = perform(
            args.ctid, args.workspace, args.daily, args.weekly, args.monthly
        )
    print(
        f"PASS: encrypted backup restored and verified; retention complete; snapshot {snapshot_id}"
    )


if __name__ == "__main__":
    try:
        main()
    except (RuntimeError, ValueError, KeyError, OSError) as exc:
        # Never print arbitrary command output, paths or secret content on failure.
        raise SystemExit(
            f"FAIL: backup aborted ({type(exc).__name__}); inspect the stage privately"
        ) from None
