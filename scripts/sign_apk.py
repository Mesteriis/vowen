"""Sign an unsigned release APK using owner-only local files, never passwords in argv."""

import argparse
import hashlib
import json
import os
import stat
import subprocess
from pathlib import Path


def private_file(path: Path) -> None:
    mode = path.lstat()
    if (
        not stat.S_ISREG(mode.st_mode)
        or mode.st_uid != os.getuid()
        or mode.st_mode & 0o077
    ):
        raise ValueError("Signing keys/passwords must be owner-only regular files")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--unsigned", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--keystore", type=Path, required=True)
    parser.add_argument("--password-file", type=Path, required=True)
    parser.add_argument("--alias", default="vowen")
    args = parser.parse_args()
    for file in (args.keystore, args.password_file):
        private_file(file)
    if args.output.exists():
        parser.error("Refusing to overwrite an existing signed APK")
    sdk = os.environ.get("ANDROID_HOME") or os.environ.get("ANDROID_SDK_ROOT")
    if not sdk:
        parser.error("Set ANDROID_HOME")
    signer = str(Path(sdk) / "build-tools/36.0.0/apksigner")
    subprocess.run(
        [
            signer,
            "sign",
            "--ks",
            str(args.keystore),
            "--ks-key-alias",
            args.alias,
            "--ks-pass",
            f"file:{args.password_file}",
            "--key-pass",
            f"file:{args.password_file}",
            "--v1-signing-enabled",
            "false",
            "--out",
            str(args.output),
            str(args.unsigned),
        ],
        check=True,
    )
    result = subprocess.run(
        [signer, "verify", "--verbose", "--print-certs", str(args.output)],
        check=True,
        capture_output=True,
        text=True,
    )
    # Certificate SHA is public metadata. The keystore and password never leave this machine.
    cert = next(
        line.partition(": ")[2]
        for line in result.stdout.splitlines()
        if line.startswith("Signer #1 certificate SHA-256 digest:")
    )
    sha = hashlib.sha256(args.output.read_bytes()).hexdigest()
    manifest = {
        "sha256": sha,
        "unsigned_sha256": hashlib.sha256(args.unsigned.read_bytes()).hexdigest(),
        "certificate_sha256": cert,
        "signing": "personal release key; APK v2/v3, no debug key",
    }
    args.output.with_suffix(".json").write_text(json.dumps(manifest, indent=2) + "\n")
    args.output.with_suffix(".sha256").write_text(f"{sha}  {args.output.name}\n")
    print(
        "PASS: personal release APK signed and verified (not installed on any device)"
    )


if __name__ == "__main__":
    main()
