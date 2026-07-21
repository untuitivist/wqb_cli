from __future__ import annotations

import hashlib
import json
import os
import re
import stat
import subprocess
import sys
from dataclasses import dataclass
from math import isfinite
from pathlib import Path
from typing import Any

from . import artifacts as artifact_limits
from .artifacts import (
    ArtifactError,
    ArtifactWriter,
    _strict_json_decoder,
    redact_argv,
    redact_json,
    redact_text,
)
from .context import _is_secret_key
from .policy import AgentPolicy, PolicyViolation
from .types import RunState, WorkflowNode


PACKAGE_ROOT = Path(__file__).resolve().parent.parent
REPO_ROOT = PACKAGE_ROOT
MAX_FINGERPRINT_FILE_BYTES = 32 * 1024 * 1024
RESOURCE_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]{0,255}")
FILE_INPUT_FLAGS = {
    ("sim", "create"): frozenset({"--input"}),
    ("scope", "files"): frozenset({"--info", "--pickle"}),
    ("scope", "list"): frozenset({"--info", "--pickle"}),
    ("scope", "show"): frozenset({"--info", "--pickle"}),
    ("scope", "top"): frozenset({"--info", "--pickle"}),
    ("scope", "alpha-rows"): frozenset({"--info", "--pickle"}),
    ("community", "search"): frozenset({"--sqlite"}),
}
DEFAULT_FILE_PROBES = {
    ("scope", "files"): (
        ("--info", "local/data_all/info_data.bin"),
        ("--pickle", "local/data_all/all_data.pickle"),
    ),
}
AUTH_SENSITIVE_READ_PREFIXES = (
    ("auth", "status"),
    ("user",),
    ("event",),
    ("data",),
    ("alpha", "list"),
    ("alpha", "get"),
    ("alpha", "check"),
    ("alpha", "recordsets"),
    ("alpha", "correlation"),
    ("alpha", "performance-comparison"),
    ("sim", "get"),
    ("sim", "options"),
    ("search",),
)
EXTERNAL_NODE_COMMANDS = {
    WorkflowNode.G: (("arxiv", "search", "query"), ("arxiv", "search", "raw"))
}


class RunnerError(RuntimeError):
    """Raised when a restricted command cannot be completed safely."""


@dataclass(frozen=True)
class RunnerResult:
    payload: dict[str, Any]
    artifact: Any
    reused: bool
    command_id: int
    returncode: int


@dataclass(frozen=True)
class _ExecutableIdentity:
    path: Path
    sha256: str
    size: int
    device: int
    inode: int


@dataclass(frozen=True)
class _InputSnapshot:
    path: Path
    sha256: str
    size: int


@dataclass(frozen=True)
class _PreparedInvocation:
    argv: tuple[str, ...]
    fingerprint: str
    snapshots: tuple[_InputSnapshot, ...]
    missing_input: bool


def _is_link(path: Path) -> bool:
    is_junction = getattr(path, "is_junction", None)
    return path.is_symlink() or (callable(is_junction) and is_junction())


def sanitized_environment() -> dict[str, str]:
    allowed = {
        "PATH",
        "PATHEXT",
        "SYSTEMROOT",
        "WINDIR",
        "COMSPEC",
        "TEMP",
        "TMP",
        "HOME",
        "USERPROFILE",
        "APPDATA",
        "LOCALAPPDATA",
        "PROGRAMDATA",
        "VIRTUAL_ENV",
        "LANG",
        "LC_ALL",
    }
    result: dict[str, str] = {}
    for key, value in os.environ.items():
        if key.upper() not in allowed:
            continue
        if _is_secret_key(key) or key.casefold() in {"wqb_email", "email"}:
            continue
        result[key] = value
    return result


def _contains_http_status(value: object, statuses: set[int]) -> bool:
    if isinstance(value, dict):
        if value.get("status_code") in statuses:
            return True
        return any(_contains_http_status(item, statuses) for item in value.values())
    if isinstance(value, (list, tuple)):
        return any(_contains_http_status(item, statuses) for item in value)
    return False


def _capture_file_argument(token: str, *, cwd: Path) -> tuple[dict[str, Any], bytes] | None:
    candidate = Path(token).expanduser()
    if not candidate.is_absolute():
        candidate = cwd / candidate
    descriptor: int | None = None
    try:
        if _is_link(candidate):
            raise RunnerError("command file arguments must not be symbolic links")
        if not candidate.exists():
            return None
        flags = os.O_RDONLY | getattr(os, "O_BINARY", 0)
        flags |= getattr(os, "O_NOFOLLOW", 0)
        descriptor = os.open(candidate, flags)
        before = os.fstat(descriptor)
        if not stat.S_ISREG(before.st_mode):
            raise RunnerError("command file arguments must be regular files")
        if before.st_size > MAX_FINGERPRINT_FILE_BYTES:
            raise RunnerError("command file argument exceeds the fingerprint size limit")
        digest = hashlib.sha256()
        consumed = 0
        chunks: list[bytes] = []
        with os.fdopen(descriptor, "rb") as stream:
            descriptor = None
            while chunk := stream.read(1024 * 1024):
                consumed += len(chunk)
                if consumed > MAX_FINGERPRINT_FILE_BYTES:
                    raise RunnerError(
                        "command file argument exceeds the fingerprint size limit"
                    )
                chunks.append(chunk)
                digest.update(chunk)
            after = os.fstat(stream.fileno())
        before_identity = (
            before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns
        )
        after_identity = (
            after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns
        )
        if before_identity != after_identity or consumed != before.st_size:
            raise RunnerError("command file argument changed while it was read")
        identity = {"file": {"sha256": digest.hexdigest(), "size": consumed}}
        return identity, b"".join(chunks)
    except OSError:
        raise RunnerError("command file argument cannot be inspected") from None
    finally:
        if descriptor is not None:
            os.close(descriptor)


def _file_identity(token: str, *, cwd: Path) -> Any:
    captured = _capture_file_argument(token, cwd=cwd)
    return token if captured is None else captured[0]


def _fingerprint_from_normalized(node: WorkflowNode, normalized: list[Any]) -> str:
    canonical = json.dumps(
        {"node": node.value, "argv": normalized},
        ensure_ascii=True,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def _default_file_probe_identities(
    argv: tuple[str, ...], *, cwd: Path
) -> list[dict[str, Any]]:
    explicit = {token.partition("=")[0].casefold() for token in argv}
    identities: list[dict[str, Any]] = []
    probes = list(DEFAULT_FILE_PROBES.get(argv[:2], ()))
    if any(argv[: len(prefix)] == prefix for prefix in AUTH_SENSITIVE_READ_PREFIXES):
        probes.append(("--auth-cookie", "local/auth/cookies.json"))
    for flag, relative_path in probes:
        if flag.casefold() in explicit:
            continue
        path = cwd / relative_path
        try:
            if _is_link(path):
                raise RunnerError("default command file must not be a symbolic link")
            details = path.stat()
        except FileNotFoundError:
            identity: dict[str, Any] = {"exists": False}
        except OSError:
            raise RunnerError("default command file cannot be inspected") from None
        else:
            if not stat.S_ISREG(details.st_mode):
                raise RunnerError("default command file must be a regular file")
            identity = {
                "exists": True,
                "size": details.st_size,
                "mtime_ns": details.st_mtime_ns,
            }
        identities.append({"default_file": flag, "identity": identity})
    return identities


def command_fingerprint(
    node: WorkflowNode, argv: tuple[str, ...], *, cwd: Path = REPO_ROOT
) -> str:
    cwd = Path(cwd).expanduser().resolve()
    input_flags = FILE_INPUT_FLAGS.get(argv[:2], frozenset())
    normalized: list[Any] = []
    index = 0
    while index < len(argv):
        token = argv[index]
        flag, separator, value = token.partition("=")
        normalized_flag = flag.casefold()
        if separator and value and normalized_flag in input_flags:
            identity = _file_identity(value, cwd=cwd)
            normalized.append({"flag": flag, "value": identity})
        elif normalized_flag in input_flags and index + 1 < len(argv):
            next_token = argv[index + 1]
            identity = _file_identity(next_token, cwd=cwd)
            normalized.append({"flag": token, "value": identity})
            index += 1
        else:
            normalized.append(token)
        index += 1
    normalized.extend(_default_file_probe_identities(argv, cwd=cwd))
    return _fingerprint_from_normalized(node, normalized)


class AgentRunner:
    def __init__(
        self,
        store: Any,
        policy: AgentPolicy,
        artifacts: ArtifactWriter,
        timeout_seconds: float = 900,
        arxiv_executable: str | Path | None = None,
        command_cwd: str | Path = PACKAGE_ROOT,
    ) -> None:
        if store is None:
            raise TypeError("store must not be None")
        if type(policy) is not AgentPolicy:
            raise TypeError("policy must be an AgentPolicy")
        if type(artifacts) is not ArtifactWriter:
            raise TypeError("artifacts must be an ArtifactWriter")
        if (
            type(timeout_seconds) not in {int, float}
            or not isfinite(timeout_seconds)
            or timeout_seconds <= 0
        ):
            raise ValueError("timeout_seconds must be a finite positive number")
        self.store = store
        self.policy = policy
        self.artifacts = artifacts.with_store(store)
        self.timeout_seconds = timeout_seconds
        try:
            cwd = Path(command_cwd).expanduser()
        except TypeError:
            raise TypeError("command_cwd must be a path") from None
        if _is_link(cwd):
            raise RunnerError("command_cwd must not be a symbolic link")
        try:
            self.command_cwd = cwd.resolve(strict=True)
        except OSError:
            raise RunnerError("command_cwd cannot be resolved") from None
        if not self.command_cwd.is_dir():
            raise RunnerError("command_cwd must be a directory")
        if arxiv_executable is None:
            self.arxiv_executable = None
            self._arxiv_identity = None
        else:
            self.arxiv_executable = self._resolve_external_executable(
                arxiv_executable
            )
            self._arxiv_identity = self._capture_executable_identity(
                self.arxiv_executable
            )

    def run(
        self,
        run_id: str,
        node: WorkflowNode,
        argv: tuple[str, ...],
        artifact_name: str,
    ) -> RunnerResult:
        self.policy.require_command(node, argv)
        self.artifacts.validate(run_id, node, artifact_name)
        return self._run(
            run_id,
            node,
            argv,
            artifact_name,
            [sys.executable, "-m", "wqb_cli", *argv],
            external=False,
        )

    def run_external(
        self,
        run_id: str,
        node: WorkflowNode,
        argv: tuple[str, ...],
        artifact_name: str,
    ) -> RunnerResult:
        if type(node) is not WorkflowNode or type(argv) is not tuple:
            raise PolicyViolation("external command input is invalid")
        prefixes = EXTERNAL_NODE_COMMANDS.get(node, ())
        if not any(argv[: len(prefix)] == prefix for prefix in prefixes):
            raise PolicyViolation("external command is not allowed")
        if not argv or any(type(token) is not str or not token.strip() for token in argv):
            raise PolicyViolation("external command argv is invalid")
        self.artifacts.validate(run_id, node, artifact_name)
        executable = self._require_external_identity()
        return self._run(
            run_id,
            node,
            argv,
            artifact_name,
            [str(executable), *argv[1:]],
            external=True,
        )

    @staticmethod
    def _resolve_external_executable(configured: str | Path) -> Path:
        try:
            raw = os.fspath(configured)
        except TypeError:
            raise TypeError("arxiv_executable must be a path") from None
        path = Path(raw).expanduser()
        if not path.is_absolute():
            raise RunnerError("arxiv executable must be an absolute configured path")
        if _is_link(path):
            raise RunnerError("arxiv executable must not be a symbolic link")
        try:
            resolved = path.resolve(strict=True)
        except OSError:
            raise RunnerError("arxiv executable cannot be resolved") from None
        if not resolved.is_file():
            raise RunnerError("arxiv executable must be a file")
        stem = resolved.stem.casefold()
        if "arxiv" not in stem:
            raise RunnerError("configured executable is not an arxiv entrypoint")
        forbidden_suffixes = {".bat", ".cmd", ".ps1", ".py", ".sh"}
        if resolved.suffix.casefold() in forbidden_suffixes:
            raise RunnerError("arxiv executable must not be an interpreter or shell")
        return resolved

    @staticmethod
    def _capture_executable_identity(path: Path) -> _ExecutableIdentity:
        try:
            before = path.stat()
            digest = hashlib.sha256()
            with path.open("rb") as stream:
                while chunk := stream.read(1024 * 1024):
                    digest.update(chunk)
            after = path.stat()
        except OSError:
            raise RunnerError("arxiv executable identity cannot be read") from None
        before_identity = (
            before.st_dev,
            before.st_ino,
            before.st_size,
            before.st_mtime_ns,
        )
        after_identity = (
            after.st_dev,
            after.st_ino,
            after.st_size,
            after.st_mtime_ns,
        )
        if before_identity != after_identity:
            raise RunnerError("arxiv executable changed during validation")
        return _ExecutableIdentity(
            path=path,
            sha256=digest.hexdigest(),
            size=after.st_size,
            device=after.st_dev,
            inode=after.st_ino,
        )

    def _require_external_identity(self) -> Path:
        expected = self._arxiv_identity
        path = self.arxiv_executable
        if expected is None or path is None:
            raise RunnerError("arxiv executable is not configured")
        if _is_link(path):
            raise RunnerError("arxiv executable identity changed")
        try:
            resolved = path.resolve(strict=True)
        except OSError:
            raise RunnerError("arxiv executable identity changed") from None
        if resolved != expected.path:
            raise RunnerError("arxiv executable identity changed")
        actual = self._capture_executable_identity(path)
        if actual != expected:
            raise RunnerError("arxiv executable identity changed")
        return path

    def _run(
        self,
        run_id: str,
        node: WorkflowNode,
        argv: tuple[str, ...],
        artifact_name: str,
        command_line: list[str],
        *,
        external: bool,
    ) -> RunnerResult:
        if self.store.get_run(run_id).state is RunState.STOPPED:
            raise RunnerError("run has been manually stopped")
        prebound_resource_id = self._prebound_resource_id(argv)
        prepared = self._prepare_invocation(run_id, node, argv)
        fingerprint = prepared.fingerprint
        command = self.store.reserve_command(
            run_id, node, fingerprint, redact_argv(argv)
        )
        if command.status == "COMPLETED":
            if command.artifact_id is None:
                raise RunnerError("completed command has no artifact")
            artifact = self.store.get_artifact(command.artifact_id)
            payload = self.artifacts.read_json(artifact)
            if self._retryable_completed_auth_rejection(argv, command, payload):
                try:
                    command = self.store.restart_rejected_command(command.id)
                except Exception:
                    raise RunnerError(
                        "rejected command could not be reopened after authentication"
                    ) from None
            else:
                return RunnerResult(
                    payload,
                    artifact,
                    True,
                    command.id,
                    getattr(command, "exit_code", None) or 0,
                )

        effective_argv = prepared.argv
        if external:
            effective_line = [command_line[0], *effective_argv[1:]]
        else:
            effective_line = [sys.executable, "-m", "wqb_cli", *effective_argv]
        if command.status == "RECOVERY_REQUIRED":
            effective_argv = self._recovery_argv(node, argv, command.resource_id)
            if external:
                effective_line = [command_line[0], *effective_argv[1:]]
            else:
                effective_line = [sys.executable, "-m", "wqb_cli", *effective_argv]
        elif command.status != "STARTED":
            raise RunnerError("command ledger status does not permit execution")
        elif prepared.missing_input:
            raise RunnerError("command file argument does not exist")

        bound_resource_id = command.resource_id
        if command.status == "STARTED" and prebound_resource_id is not None:
            try:
                self.store.mark_command_resource(command.id, prebound_resource_id)
            except Exception:
                raise RunnerError("command resource could not be persisted") from None
            bound_resource_id = prebound_resource_id

        if command.status == "STARTED":
            try:
                for snapshot in prepared.snapshots:
                    self.artifacts.verify_input_snapshot(
                        snapshot.path, snapshot.sha256, snapshot.size
                    )
            except ArtifactError:
                raise RunnerError("command input snapshot identity changed") from None
        environment = sanitized_environment()
        if external:
            executable = self._require_external_identity()
            effective_line[0] = str(executable)

        try:
            completed = subprocess.run(
                effective_line,
                cwd=self.command_cwd,
                shell=False,
                text=True,
                encoding="utf-8",
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=self.timeout_seconds,
                check=False,
                env=environment,
            )
        except subprocess.TimeoutExpired:
            if self._is_mutation(argv):
                self._recoverable_log(
                    command,
                    run_id,
                    node,
                    argv,
                    fingerprint,
                    "TIMEOUT",
                    None,
                    "",
                    prebound_resource_id,
                )
            else:
                self._fail(command, run_id, node, argv, fingerprint, "TIMEOUT", None, "")
            raise RunnerError("command timed out") from None
        except OSError:
            if self._is_mutation(argv):
                self._recoverable_log(
                    command,
                    run_id,
                    node,
                    argv,
                    fingerprint,
                    "EXECUTION_UNKNOWN",
                    None,
                    "",
                    prebound_resource_id,
                )
            else:
                self._fail(command, run_id, node, argv, fingerprint, "EXECUTION_ERROR", None, "")
            raise RunnerError("command execution failed") from None

        try:
            payload = self._parse_stdout(completed.stdout)
        except RunnerError:
            failure_status = (
                "NONZERO_EXIT" if completed.returncode != 0 else "INVALID_OUTPUT"
            )
            if self._is_mutation(argv):
                self._recoverable_log(
                    command,
                    run_id,
                    node,
                    argv,
                    fingerprint,
                    failure_status,
                    completed.returncode,
                    completed.stderr,
                    prebound_resource_id,
                )
            else:
                self._fail(
                    command,
                    run_id,
                    node,
                    argv,
                    fingerprint,
                    failure_status,
                    completed.returncode,
                    completed.stderr,
                )
            raise

        confirmed_simulation_rejection = (
            argv[:2] == ("sim", "create")
            and completed.returncode != 0
            and payload.get("ok") is False
            and "simulation_id" in payload
            and payload["simulation_id"] is None
        )
        confirmed_read_rejection = (
            not self._is_mutation(effective_argv)
            and completed.returncode != 0
            and payload.get("ok") is False
        )
        recovery_read_rejection = (
            command.status == "RECOVERY_REQUIRED" and confirmed_read_rejection
        )
        resource_payload = payload
        if confirmed_simulation_rejection:
            resource_payload = dict(payload)
            resource_payload.pop("simulation_id")
        try:
            resource_id = self._resource_id(argv, resource_payload)
        except RunnerError:
            if self._is_mutation(argv):
                self._recoverable_log(
                    command,
                    run_id,
                    node,
                    argv,
                    fingerprint,
                    "RESOURCE_CONFLICT",
                    completed.returncode,
                    completed.stderr,
                    bound_resource_id,
                )
            raise
        if resource_id is not None and bound_resource_id is None:
            try:
                self.store.mark_command_resource(command.id, resource_id)
            except Exception:
                raise RunnerError("command resource could not be persisted") from None
            bound_resource_id = resource_id
        elif resource_id is not None and resource_id != bound_resource_id:
            if self._is_mutation(argv):
                self._recoverable_log(
                    command,
                    run_id,
                    node,
                    argv,
                    fingerprint,
                    "RESOURCE_CONFLICT",
                    completed.returncode,
                    completed.stderr,
                    bound_resource_id,
                )
            raise RunnerError("command resource conflicts with its ledger binding")

        confirmed_simulation_rejection = (
            confirmed_simulation_rejection and resource_id is None
        )
        if completed.returncode != 0 and not (
            confirmed_simulation_rejection or confirmed_read_rejection
        ):
            if self._is_mutation(argv):
                self._recoverable_log(
                    command,
                    run_id,
                    node,
                    argv,
                    fingerprint,
                    "NONZERO_EXIT",
                    completed.returncode,
                    completed.stderr,
                    bound_resource_id,
                )
            else:
                self._fail(
                    command,
                    run_id,
                    node,
                    argv,
                    fingerprint,
                    "NONZERO_EXIT",
                    completed.returncode,
                    completed.stderr,
                )
            raise RunnerError("command exited with a nonzero status")
        safe_payload = redact_json(payload)

        artifact = None
        try:
            artifact = self.artifacts.write_json(
                run_id, node, artifact_name, safe_payload
            )
            self._write_log(
                run_id,
                node,
                argv,
                fingerprint,
                "RECOVERY_REQUIRED" if recovery_read_rejection else "COMPLETED",
                completed.returncode,
                completed.stderr,
                artifact,
                resource_id or command.resource_id,
            )
            if recovery_read_rejection:
                self.store.record_command_recovery_artifact(
                    command.id, completed.returncode, artifact.id
                )
            else:
                self.store.complete_command(
                    command.id, completed.returncode, artifact_id=artifact.id
                )
        except Exception:
            if not self._is_mutation(argv):
                try:
                    self.store.fail_command(
                        command.id,
                        "command result persistence failed",
                        exit_code=completed.returncode,
                        artifact_id=getattr(artifact, "id", None),
                    )
                except Exception:
                    pass
            raise RunnerError("command result could not be persisted") from None
        return RunnerResult(
            safe_payload, artifact, False, command.id, completed.returncode
        )

    def _prepare_invocation(
        self, run_id: str, node: WorkflowNode, argv: tuple[str, ...]
    ) -> _PreparedInvocation:
        input_flags = FILE_INPUT_FLAGS.get(argv[:2], frozenset())
        normalized: list[Any] = []
        effective: list[str] = []
        snapshots: list[_InputSnapshot] = []
        captured_by_path: dict[str, tuple[dict[str, Any], bytes] | None] = {}
        missing_input = False

        def capture(token: str) -> tuple[Any, Path | None]:
            nonlocal missing_input
            candidate = Path(token).expanduser()
            if not candidate.is_absolute():
                candidate = self.command_cwd / candidate
            key = os.path.normcase(str(candidate.absolute()))
            if key not in captured_by_path:
                captured_by_path[key] = _capture_file_argument(
                    token, cwd=self.command_cwd
                )
            captured = captured_by_path[key]
            if captured is None:
                missing_input = True
                return token, None
            identity, content = captured
            digest = identity["file"]["sha256"]
            size = identity["file"]["size"]
            try:
                path = self.artifacts.stage_input(
                    run_id,
                    node,
                    content,
                    digest,
                    require_utf8_text=argv[:2] == ("sim", "create"),
                )
            except ArtifactError:
                raise RunnerError("command input snapshot could not be staged") from None
            snapshot = _InputSnapshot(path, digest, size)
            if snapshot not in snapshots:
                snapshots.append(snapshot)
            return identity, path

        index = 0
        while index < len(argv):
            token = argv[index]
            flag, separator, value = token.partition("=")
            normalized_flag = flag.casefold()
            if separator and value and normalized_flag in input_flags:
                identity, snapshot_path = capture(value)
                normalized.append({"flag": flag, "value": identity})
                effective.append(
                    token if snapshot_path is None else f"{flag}={snapshot_path}"
                )
            elif normalized_flag in input_flags and index + 1 < len(argv):
                next_token = argv[index + 1]
                identity, snapshot_path = capture(next_token)
                normalized.append({"flag": token, "value": identity})
                effective.extend(
                    (token, next_token if snapshot_path is None else str(snapshot_path))
                )
                index += 1
            else:
                normalized.append(token)
                effective.append(token)
            index += 1
        normalized.extend(
            _default_file_probe_identities(argv, cwd=self.command_cwd)
        )
        return _PreparedInvocation(
            tuple(effective),
            _fingerprint_from_normalized(node, normalized),
            tuple(snapshots),
            missing_input,
        )

    def _recovery_argv(
        self, node: WorkflowNode, argv: tuple[str, ...], resource_id: str | None
    ) -> tuple[str, ...]:
        if argv[:2] == ("sim", "create"):
            if not resource_id:
                raise RunnerError("simulation recovery requires a resource id")
            recovery = ("sim", "get", resource_id, "--max-wait-seconds", "900")
            self.policy.require_command(node, recovery)
            return recovery
        if argv[:2] == ("alpha", "submit"):
            if not resource_id:
                raise RunnerError("submission recovery requires a resource id")
            recovery = ("alpha", "get", resource_id)
            self.policy.require_command(node, recovery)
            return recovery
        raise RunnerError("command recovery is not explicitly supported")

    @staticmethod
    def _parse_stdout(stdout: str) -> dict[str, Any]:
        if len(stdout) > artifact_limits.MAX_JSON_CHARS:
            raise RunnerError("command output exceeds the JSON character limit")
        decoder = _strict_json_decoder()
        try:
            start = len(stdout) - len(stdout.lstrip())
            value, end = decoder.raw_decode(stdout, start)
            if stdout[end:].strip() or type(value) is not dict:
                raise ValueError("extra output")
            value = redact_json(value)
        except (ArtifactError, json.JSONDecodeError, ValueError):
            raise RunnerError("command output must be exactly one JSON object") from None
        return value

    @staticmethod
    def _resource_id(argv: tuple[str, ...], payload: dict[str, Any]) -> str | None:
        if argv[:2] not in {("sim", "create"), ("alpha", "submit")}:
            return None
        for field in ("alpha_id", "simulation_id", "id"):
            if field not in payload:
                continue
            value = payload[field]
            if type(value) is not str or RESOURCE_ID.fullmatch(value) is None:
                raise RunnerError(
                    "command resource conflicts with its ledger binding: invalid field"
                )
        if argv[:2] == ("sim", "create"):
            value = payload.get("simulation_id", payload.get("id"))
            if value is None:
                return None
            return value
        value: Any = None
        if argv[:2] == ("alpha", "submit"):
            if "alpha_id" in payload:
                value = payload["alpha_id"]
            elif "id" in payload:
                value = payload["id"]
            else:
                value = argv[2] if len(argv) > 2 else None
        return value if type(value) is str and RESOURCE_ID.fullmatch(value) else None

    @staticmethod
    def _prebound_resource_id(argv: tuple[str, ...]) -> str | None:
        if argv[:2] != ("alpha", "submit"):
            return None
        if len(argv) < 3 or RESOURCE_ID.fullmatch(argv[2]) is None:
            raise RunnerError("alpha submit requires a valid alpha id")
        return argv[2]

    @staticmethod
    def _is_mutation(argv: tuple[str, ...]) -> bool:
        return argv[:2] in {("sim", "create"), ("alpha", "submit")}

    @staticmethod
    def _retryable_completed_auth_rejection(
        argv: tuple[str, ...], command: Any, payload: object
    ) -> bool:
        return (
            argv[:2] == ("sim", "create")
            and getattr(command, "resource_id", None) is None
            and getattr(command, "exit_code", None) not in {None, 0}
            and isinstance(payload, dict)
            and payload.get("ok") is False
            and payload.get("simulation_id") is None
            and _contains_http_status(payload, {401, 403})
        )

    def _recoverable_log(
        self,
        command: Any,
        run_id: str,
        node: WorkflowNode,
        argv: tuple[str, ...],
        fingerprint: str,
        status: str,
        returncode: int | None,
        stderr: str,
        resource_id: str | None,
    ) -> None:
        try:
            self._write_log(
                run_id,
                node,
                argv,
                fingerprint,
                status,
                returncode,
                stderr,
                None,
                resource_id or command.resource_id,
            )
        except Exception:
            pass

    def _fail(
        self,
        command: Any,
        run_id: str,
        node: WorkflowNode,
        argv: tuple[str, ...],
        fingerprint: str,
        status: str,
        returncode: int | None,
        stderr: str,
    ) -> None:
        try:
            self._write_log(
                run_id,
                node,
                argv,
                fingerprint,
                status,
                returncode,
                stderr,
                None,
                command.resource_id,
            )
        finally:
            self.store.fail_command(command.id, status, exit_code=returncode)

    def _write_log(
        self,
        run_id: str,
        node: WorkflowNode,
        argv: tuple[str, ...],
        fingerprint: str,
        status: str,
        returncode: int | None,
        stderr: str,
        artifact: Any,
        resource_id: str | None,
    ) -> None:
        record = {
            "argv": list(redact_argv(argv)),
            "fingerprint": fingerprint,
            "status": status,
            "returncode": returncode,
            "stderr": redact_text(stderr),
            "artifact_id": getattr(artifact, "id", None),
            "resource_id": resource_id,
        }
        self.artifacts.append_jsonl(run_id, node, "commands.jsonl", record)
