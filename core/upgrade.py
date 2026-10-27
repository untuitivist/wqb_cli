from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import sysconfig
import tempfile
import time
from email.parser import BytesParser
from importlib import metadata
from pathlib import Path
from typing import Any
from urllib.parse import urljoin, urlsplit
from zipfile import BadZipFile, ZipFile

import requests
from packaging.requirements import Requirement
from packaging.version import Version

from .. import __version__


REPOSITORY = "untuitivist/wqb_cli"
API_ROOT = f"https://api.github.com/repos/{REPOSITORY}"
RELEASE_ROOT = f"https://github.com/{REPOSITORY}/releases"
DOWNLOAD_HOSTS = {"api.github.com", "github.com", "release-assets.githubusercontent.com", "objects.githubusercontent.com"}
MAX_WHEEL_BYTES = 64 * 1024 * 1024
MAX_METADATA_BYTES = 1024 * 1024


class UpgradeError(Exception):
    def __init__(self, reason: str, detail: str, **evidence: Any) -> None:
        super().__init__(detail)
        self.reason = reason
        self.evidence = evidence

    def as_dict(self) -> dict[str, Any]:
        return {"ok": False, "reason": self.reason, "detail": str(self), **self.evidence}


class GitHubAuth(requests.auth.AuthBase):
    def __init__(self, token: str | None) -> None:
        self.token = token

    def __call__(self, request: requests.PreparedRequest) -> requests.PreparedRequest:
        target = urlsplit(request.url)
        if self.token and target.scheme == "https" and target.hostname == "api.github.com" and target.port in (None, 443):
            request.headers["Authorization"] = "Bearer " + self.token
        return request


def _github_token() -> str | None:
    token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
    if token:
        return token.strip()
    executable = shutil.which("gh")
    if executable:
        try:
            result = subprocess.run([executable, "auth", "token", "--hostname", "github.com"],
                                    capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=10, check=False)
        except (OSError, subprocess.TimeoutExpired):
            return None
        if result.returncode == 0:
            return result.stdout.strip() or None
    return None


def release_version(value: str) -> str:
    version = value.removeprefix("v")
    if not re.fullmatch(r"(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)", version):
        raise UpgradeError("invalid_version", "Use a stable release version such as 0.6.3 or v0.6.3")
    return version


def _trusted_url(address: str) -> None:
    target = urlsplit(address)
    if (target.scheme != "https" or target.hostname not in DOWNLOAD_HOSTS
            or target.username or target.password or target.port not in (None, 443) or target.fragment):
        raise UpgradeError("untrusted_release_url", "The release returned an unexpected download destination")


def _fetch(session: requests.Session, address: str, limit: int, destination: Path | None = None) -> bytes:
    started = time.monotonic()
    for redirect in range(6):
        if time.monotonic() - started > 120:
            raise UpgradeError("release_download_limit", "Release download exceeded its time budget")
        _trusted_url(address)
        with session.get(address, timeout=(10, 60), stream=True, allow_redirects=False) as response:
            if response.status_code in {301, 302, 303, 307, 308}:
                if redirect == 5 or not response.headers.get("Location"):
                    raise UpgradeError("release_redirect_limit", "Release download exceeded its redirect budget")
                address = urljoin(address, response.headers["Location"])
                continue
            if response.status_code != 200:
                if response.status_code in {403, 429} and response.headers.get("X-RateLimit-Remaining") == "0":
                    raise UpgradeError("release_api_rate_limited", "GitHub API quota exhausted; set GH_TOKEN/GITHUB_TOKEN or use an authenticated gh installation",
                                       http_status=response.status_code, reset_at=response.headers.get("X-RateLimit-Reset"))
                raise UpgradeError("release_http_error", f"Release request returned HTTP {response.status_code}",
                                   http_status=response.status_code, retry_after=response.headers.get("Retry-After"))
            if int(response.headers.get("Content-Length", "0")) > limit:
                raise UpgradeError("release_too_large", "Release response exceeds the size limit")
            chunks: list[bytes] = []
            received = 0
            handle = destination.open("wb") if destination else None
            try:
                for chunk in response.iter_content(64 * 1024):
                    received += len(chunk)
                    if received > limit or time.monotonic() - started > 120:
                        raise UpgradeError("release_download_limit", "Release download exceeded its size or time budget")
                    if handle:
                        handle.write(chunk)
                    else:
                        chunks.append(chunk)
            finally:
                if handle:
                    handle.close()
            return b"".join(chunks)
    raise AssertionError("unreachable")


def _release(session: requests.Session, target_version: str | None) -> dict[str, Any]:
    endpoint = f"/releases/tags/v{target_version}" if target_version else "/releases/latest"
    release = json.loads(_fetch(session, API_ROOT + endpoint, MAX_METADATA_BYTES))
    if not isinstance(release, dict) or release.get("draft") is not False or release.get("prerelease") is not False:
        raise UpgradeError("unstable_release", "Only published stable releases can be installed")
    version = release_version(str(release.get("tag_name", "")))
    if target_version and version != target_version:
        raise UpgradeError("release_version_mismatch", "The requested tag and returned release version differ")
    wheel_name = f"wqb_cli-{version}-py3-none-any.whl"
    required = {wheel_name, "SHA256SUMS.txt"}
    assets: dict[str, dict[str, Any]] = {}
    for asset in release.get("assets", []):
        if not isinstance(asset, dict) or asset.get("name") not in required:
            continue
        name = asset["name"]
        expected_url = f"{RELEASE_ROOT}/download/v{version}/{name}"
        if (name in assets or asset.get("state") != "uploaded"
                or asset.get("browser_download_url") != expected_url):
            raise UpgradeError("invalid_release_asset", "Release assets must be unique, uploaded and belong to the selected tag")
        assets[name] = asset
    if set(assets) != required:
        raise UpgradeError("missing_release_assets", "The release needs a universal wheel and SHA256SUMS.txt")
    return {"version": version, "url": f"{RELEASE_ROOT}/tag/v{version}",
            "wheel": assets[wheel_name], "checksums": assets["SHA256SUMS.txt"]}


def _asset_digest(asset: dict[str, Any], content: bytes) -> None:
    digest = asset.get("digest")
    if digest is not None and digest != "sha256:" + hashlib.sha256(content).hexdigest():
        raise UpgradeError("asset_digest_mismatch", "Downloaded bytes do not match the GitHub asset digest")


def _verified_wheel(session: requests.Session, release: dict[str, Any], directory: Path) -> tuple[Path, str]:
    manifest = _fetch(session, release["checksums"]["browser_download_url"], MAX_METADATA_BYTES)
    _asset_digest(release["checksums"], manifest)
    matches = []
    for line in manifest.decode("utf-8").splitlines():
        match = re.fullmatch(r"([0-9a-fA-F]{64})\s+\*?([^/\\\s]+)", line)
        if match and match.group(2) == release["wheel"]["name"]:
            matches.append(match.group(1).lower())
    if len(matches) != 1:
        raise UpgradeError("invalid_checksum_manifest", "SHA256SUMS.txt must contain exactly one checksum for the selected wheel")
    wheel = directory / release["wheel"]["name"]
    _fetch(session, release["wheel"]["browser_download_url"], MAX_WHEEL_BYTES, wheel)
    content = wheel.read_bytes()
    digest = hashlib.sha256(content).hexdigest()
    if digest != matches[0]:
        raise UpgradeError("wheel_checksum_mismatch", "Wheel SHA-256 verification failed; nothing was installed")
    _asset_digest(release["wheel"], content)
    _wheel_requirements(wheel, release["version"])
    return wheel, digest


def _wheel_requirements(wheel: Path, version: str) -> None:
    expected_metadata = f"wqb_cli-{version}.dist-info/METADATA"
    try:
        with ZipFile(wheel) as archive:
            candidates = [item for item in archive.infolist() if item.filename.endswith(".dist-info/METADATA")]
            if len(candidates) != 1 or candidates[0].filename != expected_metadata or candidates[0].file_size > MAX_METADATA_BYTES:
                raise UpgradeError("invalid_wheel_metadata", "Wheel distribution identity does not match the selected release")
            package = BytesParser().parsebytes(archive.read(candidates[0]))
    except BadZipFile as error:
        raise UpgradeError("invalid_wheel", "Release asset is not a valid wheel") from error
    if package["Name"] != "wqb-cli" or package["Version"] != version:
        raise UpgradeError("invalid_wheel_metadata", "Wheel name/version does not match the selected release")
    from packaging.specifiers import SpecifierSet

    python_version = ".".join(str(part) for part in sys.version_info[:3])
    if package["Requires-Python"] and python_version not in SpecifierSet(package["Requires-Python"]):
        raise UpgradeError("incompatible_python", "The release does not support this Python version")
    missing = []
    for value in package.get_all("Requires-Dist", []):
        requirement = Requirement(value)
        if requirement.marker and not requirement.marker.evaluate({"extra": ""}):
            continue
        try:
            installed = metadata.version(requirement.name)
        except metadata.PackageNotFoundError:
            installed = None
        if requirement.url or installed is None or installed not in requirement.specifier:
            missing.append({"requirement": value, "installed": installed})
    if missing:
        raise UpgradeError("dependency_requirements_not_met", "Install the reported dependencies in this environment before retrying",
                           requirements=missing)


def _environment() -> None:
    if (sys.prefix == sys.base_prefix
            and (Path(sysconfig.get_path("stdlib")) / "EXTERNALLY-MANAGED").exists()):
        raise UpgradeError("externally_managed_environment", "Use a virtual environment or the environment's package manager")
    try:
        distribution = metadata.distribution("wqb-cli")
    except metadata.PackageNotFoundError as error:
        raise UpgradeError("not_installed", "Install a release wheel before using the updater") from error
    direct_url = json.loads(distribution.read_text("direct_url.json") or "{}")
    installed_module = Path(distribution.locate_file("wqb_cli/__init__.py")).resolve()
    current_module = Path(__file__).resolve().parents[1] / "__init__.py"
    if direct_url.get("dir_info", {}).get("editable") or installed_module != current_module:
        raise UpgradeError("source_install", "Run the installed CLI in its Python environment; source/editable checkouts are not self-updated")
    available = subprocess.run([sys.executable, "-I", "-m", "pip", "--version"],
                               capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=30, check=False)
    if available.returncode:
        raise UpgradeError("pip_unavailable", "pip is unavailable in the running Python environment")


def _install(wheel: Path, version: str) -> dict[str, Any]:
    command = [sys.executable, "-I", "-m", "pip", "--isolated", "install", "--no-input",
               "--disable-pip-version-check", "--no-index", "--no-deps", "--upgrade", "--force-reinstall", str(wheel)]
    try:
        installed = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=600, check=False)
    except subprocess.TimeoutExpired as error:
        stdout = error.stdout.decode("utf-8", errors="replace") if isinstance(error.stdout, bytes) else error.stdout
        stderr = error.stderr.decode("utf-8", errors="replace") if isinstance(error.stderr, bytes) else error.stderr
        raise UpgradeError("installation_timed_out", "pip exceeded its wait budget; verify the installed version before retrying",
                           installer={"command": command, "timeout_seconds": error.timeout, "stdout": stdout, "stderr": stderr}) from error
    evidence = {"command": command, "exit_code": installed.returncode, "stdout": installed.stdout, "stderr": installed.stderr}
    if installed.returncode:
        raise UpgradeError("installation_failed", "pip did not complete successfully; inspect the installer output before retrying", installer=evidence)
    probe = subprocess.run(
        [sys.executable, "-I", "-c", "import json, wqb_cli; from importlib.metadata import version; "
         "print(json.dumps({'runtime': wqb_cli.__version__, 'metadata': version('wqb-cli'), 'module': wqb_cli.__file__}))"],
        capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=30, check=False,
    )
    try:
        verified = json.loads(probe.stdout) if probe.returncode == 0 else {}
    except ValueError:
        verified = {}
    if verified.get("runtime") != version or verified.get("metadata") != version:
        raise UpgradeError("installation_verification_failed", "pip returned success but a fresh interpreter did not confirm the selected version",
                           installer=evidence, verification={"exit_code": probe.returncode, "stdout": probe.stdout, "stderr": probe.stderr})
    return {"installer": evidence, "verification": verified}


def upgrade(*, target_version: str | None = None, check: bool = False, dry_run: bool = False,
            reinstall: bool = False, allow_downgrade: bool = False) -> dict[str, Any]:
    target = release_version(target_version) if target_version is not None else None
    with requests.Session() as session:
        session.auth = GitHubAuth(_github_token())
        session.headers.update({"User-Agent": f"wqb-cli/{__version__}", "Accept": "application/vnd.github+json",
                                "Accept-Encoding": "identity"})
        release = _release(session, target)
        current = Version(__version__)
        selected = Version(release["version"])
        result = {"ok": True, "current_version": __version__, "target_version": release["version"],
                  "release_url": release["url"], "python": sys.executable, "check": check, "dry_run": dry_run}
        if selected < current:
            if target is None:
                return {**result, "status": "installed_newer_than_latest", "update_available": False}
            if not allow_downgrade:
                raise UpgradeError("downgrade_blocked", "An explicit older version requires --allow-downgrade",
                                   current_version=__version__, target_version=release["version"])
        if selected == current and not reinstall:
            return {**result, "status": "up_to_date", "update_available": False}
        result.update({"update_available": selected > current, "wheel_url": release["wheel"]["browser_download_url"],
                       "checksum_url": release["checksums"]["browser_download_url"]})
        if check or dry_run:
            status = "update_available" if selected > current else "reinstall_available" if selected == current else "downgrade_available"
            return {**result, "status": status if check else "planned", "installed": False}
        _environment()
        with tempfile.TemporaryDirectory(prefix="wqb-upgrade-") as temporary:
            wheel, digest = _verified_wheel(session, release, Path(temporary))
            installed = _install(wheel, release["version"])
        return {**result, "status": "updated", "installed": True, "sha256": digest, **installed}
