from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import tarfile
import tempfile
import tomllib
from email.parser import BytesParser
from pathlib import Path, PurePosixPath
from zipfile import ZipFile


ROOT = Path(__file__).resolve().parents[1]


def validate_members(names: list[str]) -> None:
    forbidden = {"local", "research_runs", "__pycache__", ".git", "build", "dist"}
    for name in names:
        path = PurePosixPath(name)
        if (path.is_absolute() or ".." in path.parts or forbidden.intersection(path.parts)
                or any(part.startswith("~") or part.startswith(".env") for part in path.parts)
                or path.suffix in {".pyc", ".pyo", ".sqlite", ".sqlite3", ".db", ".pickle"}
                or name.endswith("/commands/sim.py")):
            raise ValueError("Unexpected private, generated or obsolete package member: " + name)


def build_release(output: Path, ref: str, expected_version: str | None = None) -> dict:
    output = output.resolve()
    if output.exists() and any(output.iterdir()):
        raise FileExistsError("Use an empty output directory so old artifacts cannot enter a release: " + str(output))
    output.mkdir(parents=True, exist_ok=True)
    commit = subprocess.check_output(["git", "rev-parse", "--verify", ref + "^{commit}"], cwd=ROOT, text=True).strip()
    with tempfile.TemporaryDirectory(prefix="wqb-release-") as temporary:
        temporary_root = Path(temporary)
        source = temporary_root / "wqb_cli"
        archive_path = temporary_root / "source.zip"
        subprocess.run(["git", "archive", "--format=zip", "--output", str(archive_path), commit], cwd=ROOT, check=True)
        with ZipFile(archive_path) as archive:
            for name in archive.namelist():
                path = PurePosixPath(name)
                if path.is_absolute() or ".." in path.parts:
                    raise ValueError("Unexpected archive path")
            archive.extractall(source)
        project = tomllib.loads((source / "pyproject.toml").read_text(encoding="utf-8"))["project"]
        version = project["version"]
        if expected_version and version != expected_version.removeprefix("v"):
            raise ValueError("Release tag and package version differ")
        subprocess.run([sys.executable, "-m", "build", "--no-isolation", "--outdir", str(output), str(source)], check=True)
    wheel = output / f"wqb_cli-{version}-py3-none-any.whl"
    sdist = output / f"wqb_cli-{version}.tar.gz"
    with ZipFile(wheel) as archive:
        validate_members(archive.namelist())
        required = {"wqb_cli/core/upgrade.py", "wqb_cli/commands/upgrade.py", "wqb_cli/commands/help_center.py",
                    "wqb_cli/resources/docs/commands/upgrade/README.md"}
        if not required.issubset(archive.namelist()):
            raise ValueError("Release wheel is missing required runtime resources")
        package = BytesParser().parsebytes(archive.read(f"wqb_cli-{version}.dist-info/METADATA"))
        if package["Name"] != "wqb-cli" or package["Version"] != version:
            raise ValueError("Wheel metadata does not match the release")
        wheel_entries = len(archive.namelist())
    with tarfile.open(sdist) as archive:
        validate_members(archive.getnames())
        sdist_entries = len(archive.getnames())
    report = {"version": version, "commit": commit, "repository": "https://github.com/untuitivist/wqb_cli",
              "wheel_entries": wheel_entries, "sdist_entries": sdist_entries,
              "sha256": {artifact.name: hashlib.sha256(artifact.read_bytes()).hexdigest() for artifact in (wheel, sdist)}}
    receipt = output / "BUILD_INFO.json"
    receipt.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    artifacts = [wheel, sdist, receipt]
    checksums = "".join(f"{hashlib.sha256(artifact.read_bytes()).hexdigest()}  {artifact.name}\n" for artifact in artifacts)
    (output / "SHA256SUMS.txt").write_text(checksums, encoding="utf-8")
    print(json.dumps(report, indent=2))
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Build and validate release artifacts from an exact Git commit")
    parser.add_argument("--outdir", type=Path, default=ROOT / "dist")
    parser.add_argument("--ref", default="HEAD")
    parser.add_argument("--expected-version")
    arguments = parser.parse_args()
    build_release(arguments.outdir, arguments.ref, arguments.expected_version)
