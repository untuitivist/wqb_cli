from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from dataclasses import dataclass
from math import isfinite
from pathlib import Path
from typing import Any

from .artifacts import ArtifactWriter, redact_argv, redact_json, redact_text
from .context import _is_secret_key
from .policy import AgentPolicy, PolicyViolation
from .types import WorkflowNode


PACKAGE_ROOT = Path(__file__).resolve().parent.parent
REPO_ROOT = PACKAGE_ROOT
MAX_FINGERPRINT_FILE_BYTES = 32 * 1024 * 1024
FILE_INPUT_FLAGS = {
    ("sim", "create"): frozenset({"--input"}),
    ("scope", "files"): frozenset({"--info", "--pickle"}),
    ("scope", "list"): frozenset({"--info", "--pickle"}),
    ("scope", "show"): frozenset({"--info", "--pickle"}),
    ("scope", "top"): frozenset({"--info", "--pickle"}),
    ("scope", "alpha-rows"): frozenset({"--info", "--pickle"}),
    ("community", "search"): frozenset({"--sqlite"}),
}
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


def _file_identity(token: str, *, cwd: Path) -> Any:
    candidate = Path(token).expanduser()
    if not candidate.is_absolute():
        candidate = cwd / candidate
    try:
        if _is_link(candidate):
            raise RunnerError("command file arguments must not be symbolic links")
        if not candidate.exists():
            return token
        if not candidate.is_file():
            raise RunnerError("command file arguments must be regular files")
        size = candidate.stat().st_size
        if size > MAX_FINGERPRINT_FILE_BYTES:
            raise RunnerError("command file argument exceeds the fingerprint size limit")
        digest = hashlib.sha256()
        consumed = 0
        with candidate.open("rb") as stream:
            while chunk := stream.read(1024 * 1024):
                consumed += len(chunk)
                if consumed > MAX_FINGERPRINT_FILE_BYTES:
                    raise RunnerError(
                        "command file argument exceeds the fingerprint size limit"
                    )
                digest.update(chunk)
        return {"file": {"sha256": digest.hexdigest(), "size": consumed}}
    except OSError:
        raise RunnerError("command file argument cannot be inspected") from None


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
    canonical = json.dumps(
        {"node": node.value, "argv": normalized},
        ensure_ascii=True,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


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
        fingerprint = command_fingerprint(node, argv, cwd=self.command_cwd)
        command = self.store.reserve_command(
            run_id, node, fingerprint, redact_argv(argv)
        )
        if command.status == "COMPLETED":
            if command.artifact_id is None:
                raise RunnerError("completed command has no artifact")
            artifact = self.store.get_artifact(command.artifact_id)
            payload = self.artifacts.read_json(artifact)
            return RunnerResult(
                payload, artifact, True, command.id, getattr(command, "exit_code", None) or 0
            )

        effective_argv = argv
        effective_line = command_line
        if command.status == "RECOVERY_REQUIRED":
            effective_argv = self._recovery_argv(node, argv, command.resource_id)
            if external:
                effective_line = [command_line[0], *effective_argv[1:]]
            else:
                effective_line = [sys.executable, "-m", "wqb_cli", *effective_argv]
        elif command.status != "STARTED":
            raise RunnerError("command ledger status does not permit execution")

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
                env=sanitized_environment(),
            )
        except subprocess.TimeoutExpired:
            self._fail(command, run_id, node, argv, fingerprint, "TIMEOUT", None, "")
            raise RunnerError("command timed out") from None
        except OSError:
            self._fail(command, run_id, node, argv, fingerprint, "EXECUTION_ERROR", None, "")
            raise RunnerError("command execution failed") from None

        if completed.returncode != 0:
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
        try:
            payload = self._parse_stdout(completed.stdout)
        except RunnerError:
            self._fail(
                command,
                run_id,
                node,
                argv,
                fingerprint,
                "INVALID_OUTPUT",
                completed.returncode,
                completed.stderr,
            )
            raise

        safe_payload = redact_json(payload)

        artifact = None
        try:
            artifact = self.artifacts.write_json(
                run_id, node, artifact_name, safe_payload
            )
            resource_id = self._resource_id(argv, payload)
            if resource_id is not None and command.resource_id is None:
                self.store.mark_command_resource(command.id, resource_id)
            self._write_log(
                run_id,
                node,
                argv,
                fingerprint,
                "COMPLETED",
                completed.returncode,
                completed.stderr,
                artifact,
                resource_id or command.resource_id,
            )
            self.store.complete_command(command.id, completed.returncode, artifact_id=artifact.id)
        except Exception:
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
        decoder = json.JSONDecoder(
            parse_constant=lambda constant: (_ for _ in ()).throw(
                ValueError("non-finite number")
            )
        )
        try:
            start = len(stdout) - len(stdout.lstrip())
            value, end = decoder.raw_decode(stdout, start)
            if stdout[end:].strip() or type(value) is not dict:
                raise ValueError("extra output")
        except (json.JSONDecodeError, ValueError):
            raise RunnerError("command output must be exactly one JSON object") from None
        return value

    @staticmethod
    def _resource_id(argv: tuple[str, ...], payload: dict[str, Any]) -> str | None:
        value: Any = None
        if argv[:2] == ("sim", "create"):
            value = payload.get("simulation_id")
        elif argv[:2] == ("alpha", "submit"):
            value = payload.get("alpha_id", payload.get("id"))
        return value if type(value) is str and value.strip() else None

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
