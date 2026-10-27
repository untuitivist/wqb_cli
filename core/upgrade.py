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
    command = [sys.executable, "-I", "-X", "utf8", "-m", "pip", "--isolated", "install", "--no-input",
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


def _windows_launcher() -> bool:
    return sys.platform == "win32" and Path(sys.argv[0]).name.lower().removesuffix(".exe") == "wqb"


def _launcher_pid() -> int:
    import ctypes
    from ctypes import wintypes

    class ProcessEntry(ctypes.Structure):
        _fields_ = [("dwSize", wintypes.DWORD), ("cntUsage", wintypes.DWORD), ("th32ProcessID", wintypes.DWORD),
                    ("th32DefaultHeapID", ctypes.c_size_t), ("th32ModuleID", wintypes.DWORD),
                    ("cntThreads", wintypes.DWORD), ("th32ParentProcessID", wintypes.DWORD),
                    ("pcPriClassBase", wintypes.LONG), ("dwFlags", wintypes.DWORD), ("szExeFile", wintypes.WCHAR * 260)]

    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.CreateToolhelp32Snapshot.argtypes = [wintypes.DWORD, wintypes.DWORD]
    kernel.CreateToolhelp32Snapshot.restype = wintypes.HANDLE
    kernel.Process32FirstW.argtypes = [wintypes.HANDLE, ctypes.POINTER(ProcessEntry)]
    kernel.Process32FirstW.restype = wintypes.BOOL
    kernel.Process32NextW.argtypes = [wintypes.HANDLE, ctypes.POINTER(ProcessEntry)]
    kernel.Process32NextW.restype = wintypes.BOOL
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    kernel.CloseHandle.restype = wintypes.BOOL
    snapshot = kernel.CreateToolhelp32Snapshot(2, 0)
    if snapshot == ctypes.c_void_p(-1).value:
        raise UpgradeError("launcher_lookup_failed", "Cannot inspect the Windows launcher process chain")
    processes: dict[int, tuple[int, str]] = {}
    try:
        entry = ProcessEntry()
        entry.dwSize = ctypes.sizeof(entry)
        available = kernel.Process32FirstW(snapshot, ctypes.byref(entry))
        while available:
            processes[entry.th32ProcessID] = (entry.th32ParentProcessID, entry.szExeFile)
            available = kernel.Process32NextW(snapshot, ctypes.byref(entry))
    finally:
        kernel.CloseHandle(snapshot)
    process_id = os.getppid()
    visited: set[int] = set()
    while process_id in processes and process_id not in visited:
        visited.add(process_id)
        parent_id, name = processes[process_id]
        if name.lower() == "wqb.exe":
            return process_id
        process_id = parent_id
    raise UpgradeError("launcher_lookup_failed", "The native wqb.exe ancestor was not found; no update was started")


def _wait_process(process_id: int, timeout_seconds: int = 60) -> bool:
    if sys.platform != "win32":
        raise UpgradeError("wait_not_supported", "Process-handle waiting is available only for Windows upgrade jobs")
    import ctypes
    from ctypes import wintypes

    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    kernel.OpenProcess.restype = wintypes.HANDLE
    kernel.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
    kernel.WaitForSingleObject.restype = wintypes.DWORD
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    kernel.CloseHandle.restype = wintypes.BOOL
    handle = kernel.OpenProcess(0x00100000, False, process_id)
    if not handle:
        if ctypes.get_last_error() == 87:
            return True
        raise UpgradeError("process_wait_failed", "Cannot open the Windows upgrade process handle")
    try:
        waited = kernel.WaitForSingleObject(handle, timeout_seconds * 1000)
        if waited == 0x00000102:
            return False
        if waited != 0:
            raise UpgradeError("process_wait_failed", "Windows did not complete the process wait normally")
        return True
    finally:
        kernel.CloseHandle(handle)


def _save_receipt(path: Path, result: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    staged = path.with_name(path.name + f".{os.getpid()}.tmp")
    staged.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    staged.replace(path)


def _start_windows_job(wheel: Path, version: str, digest: str, result: dict[str, Any], output: str | None) -> dict[str, Any]:
    directory = wheel.parent
    job_path = directory / "job.json"
    receipt = directory / "result.json"
    log = directory / "install.log"
    pending = {**result, "status": "upgrade_started", "installed": False, "sha256": digest,
               "status_path": str(receipt), "log_path": str(log)}
    job = {"wheel": str(wheel), "version": version, "sha256": digest, "launcher_pid": _launcher_pid(),
           "result": pending, "output": str(Path(output).resolve()) if output else None}
    job_path.write_text(json.dumps(job), encoding="utf-8")
    _save_receipt(receipt, pending)
    try:
        with log.open("ab") as log_handle:
            process = subprocess.Popen(
                [sys.executable, "-I", "-m", "wqb_cli.core.upgrade", "--apply-job", str(job_path)],
                stdin=subprocess.DEVNULL, stdout=log_handle, stderr=subprocess.STDOUT, close_fds=True,
                creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP,
            )
    except OSError as error:
        failed = {**pending, "ok": False, "status": "failed", "reason": "upgrade_job_start_failed", "detail": str(error)}
        _save_receipt(receipt, failed)
        raise UpgradeError("upgrade_job_start_failed", "Cannot start the Windows upgrade helper", status_path=str(receipt)) from error
    pending["job_pid"] = process.pid
    _save_receipt(receipt, pending)
    return pending


def _apply_job(job_path: Path) -> int:
    job = json.loads(job_path.read_text(encoding="utf-8"))
    receipt = job_path.parent / "result.json"
    pending = json.loads(receipt.read_text(encoding="utf-8"))
    try:
        if not _wait_process(int(job["launcher_pid"])):
            raise UpgradeError("launcher_exit_timed_out", "The Windows launcher did not exit; no installation was attempted")
        pending = json.loads(receipt.read_text(encoding="utf-8"))
        version = release_version(job["version"])
        wheel = Path(job["wheel"]).resolve()
        if wheel.parent != job_path.parent.resolve() or wheel.name != f"wqb_cli-{version}-py3-none-any.whl":
            raise UpgradeError("invalid_upgrade_job", "The upgrade job does not reference its verified wheel")
        if hashlib.sha256(wheel.read_bytes()).hexdigest() != job["sha256"]:
            raise UpgradeError("wheel_checksum_mismatch", "The staged upgrade wheel changed; nothing was installed")
        _environment()
        _wheel_requirements(wheel, version)
        installed = _install(wheel, version)
        result = {**pending, "ok": True, "status": "updated", "installed": True, **installed}
    except UpgradeError as error:
        result = {**pending, **error.as_dict(), "status": "failed", "installed": False}
    except Exception as error:
        result = {**pending, "ok": False, "status": "failed", "installed": False,
                  "reason": "upgrade_job_failed", "detail": f"{type(error).__name__}: {error}"}
    _save_receipt(receipt, result)
    if job.get("output"):
        try:
            _save_receipt(Path(job["output"]), result)
        except OSError as error:
            result["output_error"] = str(error)
            _save_receipt(receipt, result)
    return 0 if result["ok"] else 1


def upgrade_status(path: str, *, wait: bool = False) -> dict[str, Any]:
    receipt = Path(path)
    result = json.loads(receipt.read_text(encoding="utf-8"))
    if not isinstance(result, dict) or "status" not in result or "ok" not in result:
        raise UpgradeError("invalid_upgrade_receipt", "The selected file is not an upgrade receipt")
    if wait and result["status"] == "upgrade_started" and result.get("job_pid"):
        completed = _wait_process(int(result["job_pid"]))
        result = json.loads(receipt.read_text(encoding="utf-8"))
        if not completed:
            result = {**result, "wait_timed_out": True}
        elif result.get("status") == "upgrade_started":
            result = {**result, "ok": False, "status": "unknown", "reason": "upgrade_job_ended_without_receipt"}
    return result


def upgrade(*, target_version: str | None = None, check: bool = False, dry_run: bool = False,
            reinstall: bool = False, allow_downgrade: bool = False, output: str | None = None) -> dict[str, Any]:
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
        if _windows_launcher():
            directory = Path(tempfile.mkdtemp(prefix="wqb-upgrade-"))
            wheel, digest = _verified_wheel(session, release, directory)
            return _start_windows_job(wheel, release["version"], digest, result, output)
        with tempfile.TemporaryDirectory(prefix="wqb-upgrade-") as temporary:
            wheel, digest = _verified_wheel(session, release, Path(temporary))
            installed = _install(wheel, release["version"])
        return {**result, "status": "updated", "installed": True, "sha256": digest, **installed}


if __name__ == "__main__":
    if len(sys.argv) != 3 or sys.argv[1] != "--apply-job":
        raise SystemExit("Use wqb upgrade to create a verified upgrade job")
    raise SystemExit(_apply_job(Path(sys.argv[2]).resolve()))
