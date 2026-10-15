"""Pull only an encrypted restic repository over SSH; publish after complete transfer."""

import argparse
import fcntl
import os
import re
import shutil
import subprocess
import tarfile
import tempfile
from pathlib import Path


def pull(host: str, remote: str, destination: Path, password_file: Path) -> None:
    if not re.fullmatch(r"[a-zA-Z0-9_.-]+", host) or not re.fullmatch(
        r"/[a-zA-Z0-9_./-]+", remote
    ):
        raise ValueError("Expected an SSH alias and a plain absolute repository path")
    if ".." in Path(remote).parts:
        raise ValueError("Parent traversal forbidden")
    from backup import private_file

    private_file(password_file)
    os.umask(0o077)
    destination.mkdir(mode=0o700, parents=True, exist_ok=True)
    if (
        destination.is_symlink()
        or destination.stat().st_uid != os.getuid()
        or destination.stat().st_mode & 0o077
    ):
        raise ValueError("Destination must be an owner-only real directory")
    with (destination / ".pull.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        with tempfile.TemporaryDirectory(
            prefix="incoming-", dir=destination
        ) as temporary:
            incoming = Path(temporary)
            encrypted = incoming / "repository.tar"
            command = (
                f"flock -s -w 60 /run/lock/vowen-backup.lock tar -C {remote} -cf - ."
            )
            with encrypted.open("xb") as stream:
                result = subprocess.run(
                    [
                        "ssh",
                        "-o",
                        "BatchMode=yes",
                        "-o",
                        "ConnectTimeout=15",
                        host,
                        command,
                    ],
                    check=False,
                    stdout=stream,
                    stderr=subprocess.PIPE,
                )
            if result.returncode:
                raise RuntimeError("SSH transfer failed; previous repository preserved")
            repository = incoming / "restic"
            repository.mkdir(mode=0o700)
            with tarfile.open(encrypted) as archive:
                # The repo should contain regular encrypted files/directories only.
                if any(
                    not (item.isfile() or item.isdir()) for item in archive.getmembers()
                ):
                    raise ValueError("Unexpected repository member type")
                archive.extractall(repository, filter="data")
            if (
                not (repository / "config").is_file()
                or not (repository / "keys").is_dir()
            ):
                raise ValueError("Not a complete restic repository")
            environment = dict(
                os.environ,
                RESTIC_REPOSITORY=str(repository),
                RESTIC_PASSWORD_FILE=str(password_file),
            )
            checked = subprocess.run(
                ["restic", "check"],
                env=environment,
                check=False,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
            )
            if checked.returncode:
                raise RuntimeError("Off-host repository verification failed")
            # Current is a symlink to immutable generations; swap only after full extraction.
            generation = destination / incoming.name.replace("incoming-", "repo-")
            repository.rename(generation)
            pointer = destination / ".next"
            if pointer.is_symlink():
                pointer.unlink()
            pointer.symlink_to(generation.name, target_is_directory=True)
            pointer.replace(destination / "current")
            for old in destination.glob("repo-*"):
                if old != generation and old.is_dir() and not old.is_symlink():
                    shutil.rmtree(old)
    print(
        "PASS: encrypted off-host repository transferred; current generation replaced"
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ssh-host", required=True)
    parser.add_argument("--remote-repository", required=True)
    parser.add_argument("--password-file", type=Path, required=True)
    parser.add_argument("--destination", type=Path, required=True)
    args = parser.parse_args()
    try:
        pull(
            args.ssh_host, args.remote_repository, args.destination, args.password_file
        )
    except (ValueError, RuntimeError, OSError):
        raise SystemExit(
            "FAIL: encrypted off-host transfer aborted; previous generation retained"
        ) from None
