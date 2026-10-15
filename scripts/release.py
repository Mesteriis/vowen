"""Build public artifacts exclusively from a clean Git revision, never the workspace."""

import argparse
import gzip
import hashlib
import json
import os
import shutil
import subprocess
import tarfile
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def run(args, **kwargs):
    return subprocess.run(args, check=True, **kwargs)


def archive_tree(tree: Path, destination: Path, epoch: int) -> None:
    with (
        destination.open("wb") as raw,
        gzip.GzipFile(filename="", fileobj=raw, mode="wb", mtime=0) as zipped,
        tarfile.open(fileobj=zipped, mode="w", format=tarfile.PAX_FORMAT) as archive,
    ):
        for path in sorted(tree.rglob("*")):
            if path.is_symlink():
                raise ValueError("Release trees must not contain symlinks")
            info = archive.gettarinfo(
                str(path), arcname=path.relative_to(tree).as_posix()
            )
            info.uid = info.gid = 0
            info.uname = info.gname = ""
            info.mtime = epoch
            info.mode = 0o755 if path.is_dir() or info.mode & 0o111 else 0o644
            info.pax_headers = {}
            if path.is_file():
                with path.open("rb") as stream:
                    archive.addfile(info, stream)
            else:
                archive.addfile(info)


def digest(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def git(*args: str) -> str:
    return subprocess.check_output(["git", "-C", str(ROOT), *args], text=True).strip()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--kind", choices=("images", "android"), required=True)
    parser.add_argument("--verify-repeat", action="store_true")
    args = parser.parse_args()
    if git("status", "--porcelain", "--untracked-files=normal"):
        parser.error("Commit or remove workspace changes before building a release")
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    revision = git("rev-parse", "HEAD")
    epoch = int(git("show", "-s", "--format=%ct", "HEAD"))
    manifest = {
        "revision": revision,
        "source_date_epoch": epoch,
        "kind": args.kind,
        "platform": "linux/amd64" if args.kind == "images" else "Android API 26+",
        "repeat_verified": False,
        "images": {},
        "apk_signing": "unsigned",
    }
    with tempfile.TemporaryDirectory(prefix="vowen-release-") as work:
        tree = Path(work) / "source"
        tree.mkdir()
        with tempfile.TemporaryFile() as source:
            run(["git", "-C", str(ROOT), "archive", revision], stdout=source)
            source.seek(0)
            with tarfile.open(fileobj=source) as archive:
                archive.extractall(tree, filter="data")
        archive_tree(tree, output / "vowen-source.tar.gz", epoch)
        if args.kind == "images":
            for name in ("backend", "web"):
                previous = None
                for attempt in range(2 if args.verify_repeat else 1):
                    image = output / f"vowen-{name}.oci.tar"
                    metadata = Path(work) / f"{name}.json"
                    run(
                        [
                            "docker",
                            "buildx",
                            "build",
                            "--platform",
                            "linux/amd64",
                            "--no-cache",
                            "--provenance=false",
                            "--sbom=false",
                            "--build-arg",
                            f"SOURCE_DATE_EPOCH={epoch}",
                            "-f",
                            str(tree / "deploy" / f"Dockerfile.{name}"),
                            "--metadata-file",
                            str(metadata),
                            "--output",
                            f"type=oci,dest={image},rewrite-timestamp=true",
                            str(tree),
                        ]
                    )
                    current = json.loads(metadata.read_text())["containerimage.digest"]
                    if previous is not None and current != previous:
                        raise RuntimeError(f"{name} repeat build digest mismatch")
                    previous = current
                manifest["images"][name] = previous
            assets = Path(work) / "assets"
            run(
                [
                    "docker",
                    "buildx",
                    "build",
                    "--platform",
                    "linux/amd64",
                    "--build-arg",
                    f"SOURCE_DATE_EPOCH={epoch}",
                    "-f",
                    str(tree / "deploy/Dockerfile.web"),
                    "--target",
                    "assets",
                    "--output",
                    f"type=local,dest={assets}",
                    str(tree),
                ]
            )
            archive_tree(assets, output / "vowen-web.tar.gz", epoch)
        else:
            environment = dict(os.environ, SOURCE_DATE_EPOCH=str(epoch))
            sdk = environment.get("ANDROID_HOME") or environment.get("ANDROID_SDK_ROOT")
            if not sdk:
                parser.error(
                    "Set ANDROID_HOME to the installed SDK (API/build-tools 36)"
                )
            previous = None
            for attempt in range(2 if args.verify_repeat else 1):
                run(
                    [
                        "./gradlew",
                        "--no-daemon",
                        "--no-build-cache",
                        "clean",
                        "testReleaseUnitTest",
                        "lintRelease",
                        "assembleRelease",
                    ],
                    cwd=tree / "android",
                    env=environment,
                )
                apk = (
                    tree
                    / "android/app/build/outputs/apk/release/app-release-unsigned.apk"
                )
                current = digest(apk)
                if previous is not None and current != previous:
                    raise RuntimeError("Unsigned APK repeat build digest mismatch")
                previous = current
            shutil.copyfile(apk, output / "vowen-unsigned.apk")
        manifest["repeat_verified"] = args.verify_repeat
    manifest["sha256"] = {
        p.name: digest(p) for p in sorted(output.iterdir()) if p.is_file()
    }
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    (output / "SHA256SUMS").write_text(
        "".join(
            f"{digest(p)}  {p.name}\n" for p in sorted(output.iterdir()) if p.is_file()
        )
    )
    print(
        f"PASS: {args.kind} artifacts built from {revision}; repeat={args.verify_repeat}"
    )


if __name__ == "__main__":
    main()
