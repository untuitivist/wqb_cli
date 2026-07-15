from __future__ import annotations

import hashlib
import json
import os
import re
import secrets
import stat
import threading
from dataclasses import dataclass
from math import isfinite
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Any, Iterable

from .context import _is_secret_key
from .types import WorkflowNode


NODE_DIRECTORIES = {
    WorkflowNode.A: "01_A",
    WorkflowNode.B: "02_B",
    WorkflowNode.C: "03_C",
    WorkflowNode.D: "04_D",
    WorkflowNode.F: "06_F",
    WorkflowNode.G: "07_G",
    WorkflowNode.H: "08_H",
    WorkflowNode.I: "09_I",
    WorkflowNode.J: "10_J",
    WorkflowNode.K: "11_K",
    WorkflowNode.L: "12_L",
    WorkflowNode.M: "13_M",
}

MAX_JSON_DEPTH = 64
MAX_JSON_NODES = 10_000
MAX_JSON_CHARS = 250_000
MAX_JSON_INTEGER_BITS = 4_096


class ArtifactError(ValueError):
    """Raised when artifact data or its filesystem location is unsafe."""


@dataclass(frozen=True)
class WrittenArtifact:
    id: int | None
    run_id: str
    node: WorkflowNode
    name: str
    path: str
    sha256: str
    kind: str


_WINDOWS_INVALID_CHARACTERS = frozenset('<>:"|?*')
_WINDOWS_RESERVED_BASES = frozenset(
    {"CON", "PRN", "AUX", "NUL", "CLOCK$"}
    | {f"COM{number}" for number in range(1, 10)}
    | {f"LPT{number}" for number in range(1, 10)}
)


def _is_link(path: Path) -> bool:
    is_junction = getattr(path, "is_junction", None)
    return path.is_symlink() or (callable(is_junction) and is_junction())


def _validate_portable_segment(segment: str) -> None:
    invalid_character = any(
        ord(character) <= 31
        or ord(character) == 127
        or character in _WINDOWS_INVALID_CHARACTERS
        for character in segment
    )
    base = segment.split(".", 1)[0].rstrip(" .").upper()
    if (
        not segment
        or segment in {".", ".."}
        or segment.endswith((".", " "))
        or invalid_character
        or base in _WINDOWS_RESERVED_BASES
    ):
        raise ArtifactError("path contains a non-portable segment")


def _validate_run_id(run_id: str) -> None:
    if (
        type(run_id) is not str
        or not run_id
        or not run_id.strip()
        or run_id in {".", ".."}
        or "\x00" in run_id
        or "/" in run_id
        or "\\" in run_id
        or PureWindowsPath(run_id).drive
        or PureWindowsPath(run_id).is_absolute()
        or PurePosixPath(run_id).is_absolute()
    ):
        raise ArtifactError("run_id must be one safe path segment")
    _validate_portable_segment(run_id)


def _validate_name(name: str) -> None:
    if (
        type(name) is not str
        or not name
        or not name.strip()
        or name in {".", ".."}
        or name.endswith(("/", "\\"))
        or "\x00" in name
    ):
        raise ArtifactError("artifact name must be a non-empty relative path")
    windows = PureWindowsPath(name)
    posix = PurePosixPath(name)
    if (
        windows.drive
        or windows.root
        or windows.is_absolute()
        or posix.is_absolute()
        or any(part in {"", ".", ".."} for part in windows.parts)
        or any(part in {"", ".", ".."} for part in posix.parts)
    ):
        raise ArtifactError("artifact name must remain below its node directory")
    for segment in re.split(r"[\\/]", name):
        _validate_portable_segment(segment)


def _redacted_json(value: Any) -> Any:
    active: set[int] = set()
    nodes = 0
    characters = 0

    def visit(item: Any, depth: int) -> Any:
        nonlocal nodes, characters
        nodes += 1
        if nodes > MAX_JSON_NODES or depth > MAX_JSON_DEPTH:
            raise ArtifactError("artifact JSON exceeds its structural limit")
        if type(item) is dict:
            identity = id(item)
            if identity in active:
                raise ArtifactError("artifact JSON must not contain cycles")
            active.add(identity)
            dynamic_secret = any(
                type(key) is str
                and key.strip().casefold() in {"key", "name", "type"}
                and type(child) is str
                and _is_secret_key(child)
                for key, child in item.items()
            )
            result: dict[str, Any] = {}
            for key, child in item.items():
                if type(key) is not str:
                    raise ArtifactError("artifact JSON object keys must be strings")
                characters += len(key)
                if characters > MAX_JSON_CHARS:
                    raise ArtifactError("artifact JSON exceeds its character limit")
                if _is_secret_key(key) or (
                    dynamic_secret and key.strip().casefold() == "value"
                ):
                    result[key] = "[REDACTED]"
                else:
                    result[key] = visit(child, depth + 1)
            active.remove(identity)
            return result
        if type(item) is list:
            identity = id(item)
            if identity in active:
                raise ArtifactError("artifact JSON must not contain cycles")
            active.add(identity)
            result = [visit(child, depth + 1) for child in item]
            active.remove(identity)
            return result
        if item is None or type(item) is bool:
            return item
        if type(item) is int:
            if item.bit_length() > MAX_JSON_INTEGER_BITS:
                raise ArtifactError("artifact JSON integer is too large")
            return item
        if type(item) is float:
            if not isfinite(item):
                raise ArtifactError("artifact JSON numbers must be finite")
            return item
        if type(item) is str:
            characters += len(item)
            if characters > MAX_JSON_CHARS:
                raise ArtifactError("artifact JSON exceeds its character limit")
            return redact_text(item)
        raise ArtifactError("artifact data must contain only JSON-native values")

    return visit(value, 0)


def redact_json(value: dict[str, Any]) -> dict[str, Any]:
    if type(value) is not dict:
        raise ArtifactError("JSON artifacts must be objects")
    return _redacted_json(value)


_TEXT_SECRET = re.compile(
    r"(?im)(?P<prefix>(?:authorization|cookie|api[_-]?key|password|secret|token)"
    r"\s*(?::|=)\s*)(?P<value>[^\r\n]+)"
)
_QUOTED_OR_UNQUOTED_PAIR = re.compile(
    r"(?i)(?P<prefix>(?P<key_quote>[\"']?)(?P<key>[a-z0-9_.-]+)"
    r"(?P=key_quote)\s*(?::|=)\s*)"
    r"(?P<value>\"(?:\\.|[^\"\\])*\"|'(?:\\.|[^'\\])*'|[^\s,;}`]+)"
)
_CLI_PAIR = re.compile(
    r"(?i)(?P<flag>--[a-z0-9][a-z0-9_-]*)"
    r"(?:(?P<equals>=)(?P<inline>[^\s]+)|\s+(?P<next>[^\s]+))"
)


def redact_text(value: str) -> str:
    if type(value) is not str:
        raise TypeError("text must be a string")

    lines: list[str] = []
    for line in value.splitlines(keepends=True):
        ending = ""
        content = line
        if content.endswith("\r\n"):
            content, ending = content[:-2], "\r\n"
        elif content.endswith(("\n", "\r")):
            content, ending = content[:-1], content[-1]
        stripped = content.strip()
        if stripped.startswith("{") and stripped.endswith("}"):
            try:
                parsed = _strict_json_object(stripped)
            except ArtifactError:
                pass
            else:
                prefix = content[: len(content) - len(content.lstrip())]
                content = prefix + _canonical_json_object(_redacted_json(parsed))
        lines.append(content + ending)
    result = "".join(lines)
    result = _TEXT_SECRET.sub(
        lambda match: match.group("prefix") + "[REDACTED]", result
    )

    def pair(match: re.Match[str]) -> str:
        if not _is_secret_key(match.group("key")):
            return match.group(0)
        raw_value = match.group("value")
        quote = raw_value[0] if raw_value[:1] in {"\"", "'"} else ""
        replacement = f"{quote}[REDACTED]{quote}" if quote else "[REDACTED]"
        return match.group("prefix") + replacement

    result = _QUOTED_OR_UNQUOTED_PAIR.sub(pair, result)

    def cli(match: re.Match[str]) -> str:
        if not _is_secret_key(match.group("flag").lstrip("-")):
            return match.group(0)
        separator = "=" if match.group("equals") else " "
        return match.group("flag") + separator + "[REDACTED]"

    return _CLI_PAIR.sub(cli, result)


def _strict_json_object(text: str) -> dict[str, Any]:
    def object_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, child in pairs:
            if key in result:
                raise ValueError("duplicate object key")
            result[key] = child
        return result

    try:
        value = json.loads(
            text,
            object_pairs_hook=object_pairs,
            parse_constant=lambda constant: (_ for _ in ()).throw(
                ValueError("non-finite number")
            ),
        )
    except (json.JSONDecodeError, ValueError):
        raise ArtifactError("text is not a strict JSON object") from None
    if type(value) is not dict:
        raise ArtifactError("text is not a strict JSON object")
    return value


def _canonical_json_object(value: dict[str, Any]) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def redact_argv(argv: tuple[str, ...]) -> tuple[str, ...]:
    output: list[str] = []
    redact_next = False
    for token in argv:
        if redact_next:
            output.append("[REDACTED]")
            redact_next = False
            continue
        flag, separator, _ = token.partition("=")
        if flag.startswith("--") and _is_secret_key(flag.lstrip("-")):
            if separator:
                output.append(f"{flag}=[REDACTED]")
            else:
                output.append(token)
                redact_next = True
        else:
            output.append(token)
    return tuple(output)


class ArtifactWriter:
    def __init__(
        self,
        root: str | Path,
        store: Any = None,
        *,
        _lock: threading.RLock | None = None,
    ) -> None:
        if not isinstance(root, (str, Path)):
            raise TypeError("root must be a path")
        self.root = Path(root).expanduser().resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self._store = store
        self._lock = threading.RLock() if _lock is None else _lock

    def with_store(self, store: Any) -> ArtifactWriter:
        if store is None:
            raise TypeError("store must not be None")
        return ArtifactWriter(self.root, store, _lock=self._lock)

    def validate(self, run_id: str, node: WorkflowNode, name: str) -> None:
        self._target(run_id, node, name, create=False)

    def _ensure_directory(self, directory: Path, *, create: bool) -> Path:
        try:
            relative = directory.relative_to(self.root)
        except ValueError:
            raise ArtifactError("artifact directory is outside the writer root") from None
        current = self.root
        for part in relative.parts:
            candidate = current / part
            try:
                if _is_link(candidate):
                    raise ArtifactError("artifact directory must not contain symlinks")
                if candidate.exists():
                    if not candidate.is_dir():
                        raise ArtifactError("artifact parent must be a directory")
                elif create:
                    if current.resolve(strict=True) != current:
                        raise ArtifactError("artifact directory identity changed")
                    candidate.mkdir()
                resolved = candidate.resolve(strict=create)
            except ArtifactError:
                raise
            except OSError:
                raise ArtifactError("artifact directory cannot be prepared") from None
            if not resolved.is_relative_to(self.root):
                raise ArtifactError("artifact directory escapes the writer root")
            current = candidate
        return current

    def _target(
        self, run_id: str, node: WorkflowNode, name: str, *, create: bool = True
    ) -> Path:
        _validate_run_id(run_id)
        if type(node) is not WorkflowNode:
            raise ArtifactError("node must be a WorkflowNode")
        _validate_name(name)
        base = self.root / run_id / NODE_DIRECTORIES[node]
        target = base / Path(name)
        self._ensure_directory(target.parent, create=create)
        try:
            if _is_link(target):
                raise ArtifactError("artifact target must not be a symlink")
            resolved_base = base.resolve(strict=False)
            resolved_target = target.resolve(strict=False)
        except OSError:
            raise ArtifactError("artifact path cannot be resolved") from None
        if (
            not resolved_base.is_relative_to(self.root)
            or not resolved_target.is_relative_to(resolved_base)
        ):
            raise ArtifactError("artifact path escapes its node directory")
        return target

    def _write(
        self,
        run_id: str,
        node: WorkflowNode,
        name: str,
        text: str,
        kind: str,
    ) -> Any:
        with self._lock:
            if os.name == "posix":
                if not self._supports_secure_dir_fd():
                    raise ArtifactError("secure dir_fd artifact writes are unavailable")
                target, digest = self._write_with_dir_fd(
                    run_id, node, name, text
                )
            elif os.name == "nt":
                target, digest = self._write_with_windows_handles(
                    run_id, node, name, text
                )
            else:
                raise ArtifactError("secure artifact writes are unavailable")
            if self._store is None:
                return WrittenArtifact(
                    None, run_id, node, name, str(target), digest, kind
                )
            try:
                return self._store.add_or_update_artifact(
                    run_id, node, name, target, digest, kind
                )
            except Exception:
                raise ArtifactError("artifact registry update failed") from None

    @staticmethod
    def _supports_secure_dir_fd() -> bool:
        return (
            os.name == "posix"
            and os.open in os.supports_dir_fd
            and os.mkdir in os.supports_dir_fd
            and os.stat in os.supports_dir_fd
            and os.unlink in os.supports_dir_fd
            and hasattr(os, "O_DIRECTORY")
            and hasattr(os, "O_NOFOLLOW")
        )

    def _write_with_windows_handles(
        self, run_id: str, node: WorkflowNode, name: str, text: str
    ) -> tuple[Path, str]:
        target = self._target(run_id, node, name)
        expected_parent = target.parent.resolve(strict=True)
        temporary = target.parent / f".{target.name}.{secrets.token_hex(12)}.tmp"
        descriptor: int | None = None
        try:
            flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
            flags |= getattr(os, "O_BINARY", 0)
            descriptor = os.open(temporary, flags, 0o600)
            actual_temporary = self._final_path_for_fd(descriptor)
            if (
                actual_temporary.parent != expected_parent
                or not actual_temporary.is_relative_to(self.root)
            ):
                raise ArtifactError("artifact temporary handle escaped its directory")
            with os.fdopen(descriptor, "w", encoding="utf-8", newline="") as stream:
                descriptor = None
                stream.write(text)
                stream.flush()
                os.fsync(stream.fileno())
            checked_target = self._target(run_id, node, name, create=False)
            if checked_target.parent.resolve(strict=True) != expected_parent:
                raise ArtifactError("artifact directory identity changed")
            os.replace(temporary, target)
            if target.parent.resolve(strict=True) != expected_parent:
                raise ArtifactError("artifact directory identity changed")
            read_flags = os.O_RDONLY | getattr(os, "O_BINARY", 0)
            descriptor = os.open(target, read_flags)
            actual_target = self._final_path_for_fd(descriptor)
            expected_target = expected_parent / target.name
            if (
                actual_target != expected_target
                or not actual_target.is_relative_to(self.root)
            ):
                raise ArtifactError("artifact target handle escaped its directory")
            digest = hashlib.sha256()
            with os.fdopen(descriptor, "rb") as stream:
                descriptor = None
                while chunk := stream.read(1024 * 1024):
                    digest.update(chunk)
            return target, digest.hexdigest()
        finally:
            if descriptor is not None:
                os.close(descriptor)
            temporary.unlink(missing_ok=True)

    @staticmethod
    def _final_path_for_fd(descriptor: int) -> Path:
        if os.name != "nt":
            raise ArtifactError("Windows handle path verification is unavailable")
        try:
            import ctypes
            import msvcrt
            from ctypes import wintypes

            handle = msvcrt.get_osfhandle(descriptor)
            get_final_path = ctypes.WinDLL(
                "kernel32", use_last_error=True
            ).GetFinalPathNameByHandleW
            get_final_path.argtypes = (
                wintypes.HANDLE,
                wintypes.LPWSTR,
                wintypes.DWORD,
                wintypes.DWORD,
            )
            get_final_path.restype = wintypes.DWORD
            buffer = ctypes.create_unicode_buffer(32_768)
            length = get_final_path(handle, buffer, len(buffer), 0)
            if length == 0 or length >= len(buffer):
                raise OSError(ctypes.get_last_error())
            raw = buffer.value
            if raw.startswith("\\\\?\\UNC\\"):
                raw = "\\\\" + raw[8:]
            elif raw.startswith("\\\\?\\"):
                raw = raw[4:]
            return Path(raw).resolve(strict=True)
        except (OSError, ValueError):
            raise ArtifactError("artifact handle path cannot be verified") from None

    def _write_with_dir_fd(
        self, run_id: str, node: WorkflowNode, name: str, text: str
    ) -> tuple[Path, str]:
        _validate_run_id(run_id)
        if type(node) is not WorkflowNode:
            raise ArtifactError("node must be a WorkflowNode")
        _validate_name(name)
        relative = Path(run_id) / NODE_DIRECTORIES[node] / Path(name)
        target = self.root / relative
        parent_fd = self._open_parent_dir_fd(relative.parent.parts)
        temporary_name = f".{relative.name}.{secrets.token_hex(12)}.tmp"
        temporary_exists = False
        try:
            try:
                existing = os.stat(
                    relative.name, dir_fd=parent_fd, follow_symlinks=False
                )
            except FileNotFoundError:
                existing = None
            if existing is not None and stat.S_ISLNK(existing.st_mode):
                raise ArtifactError("artifact target must not be a symlink")

            flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW
            flags |= getattr(os, "O_CLOEXEC", 0)
            descriptor = os.open(temporary_name, flags, 0o600, dir_fd=parent_fd)
            temporary_exists = True
            with os.fdopen(descriptor, "w", encoding="utf-8", newline="") as stream:
                stream.write(text)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(
                temporary_name,
                relative.name,
                src_dir_fd=parent_fd,
                dst_dir_fd=parent_fd,
            )
            temporary_exists = False
            read_flags = os.O_RDONLY | os.O_NOFOLLOW
            read_flags |= getattr(os, "O_CLOEXEC", 0)
            read_fd = os.open(relative.name, read_flags, dir_fd=parent_fd)
            digest = hashlib.sha256()
            with os.fdopen(read_fd, "rb") as stream:
                while chunk := stream.read(1024 * 1024):
                    digest.update(chunk)
            os.fsync(parent_fd)
            return target, digest.hexdigest()
        except ArtifactError:
            raise
        except OSError:
            raise ArtifactError("artifact could not be written securely") from None
        finally:
            if temporary_exists:
                try:
                    os.unlink(temporary_name, dir_fd=parent_fd)
                except OSError:
                    pass
            os.close(parent_fd)

    def _open_parent_dir_fd(self, parts: tuple[str, ...]) -> int:
        flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
        flags |= getattr(os, "O_CLOEXEC", 0)
        try:
            current = os.open(self.root, flags)
        except OSError:
            raise ArtifactError("artifact root cannot be opened securely") from None
        try:
            for part in parts:
                try:
                    child = os.open(part, flags, dir_fd=current)
                except FileNotFoundError:
                    os.mkdir(part, 0o700, dir_fd=current)
                    child = os.open(part, flags, dir_fd=current)
                os.close(current)
                current = child
            return current
        except OSError:
            os.close(current)
            raise ArtifactError("artifact directory cannot be opened securely") from None

    def write_json(
        self, run_id: str, node: WorkflowNode, name: str, value: dict[str, Any]
    ) -> Any:
        safe = redact_json(value)
        rendered = json.dumps(
            safe, ensure_ascii=False, allow_nan=False, sort_keys=True, separators=(",", ":")
        )
        return self._write(run_id, node, name, rendered, "json")

    def write_jsonl(
        self,
        run_id: str,
        node: WorkflowNode,
        name: str,
        values: Iterable[dict[str, Any]],
    ) -> Any:
        records: list[str] = []
        for value in values:
            if type(value) is not dict:
                raise ArtifactError("JSONL records must be objects")
            records.append(
                json.dumps(
                    _redacted_json(value),
                    ensure_ascii=False,
                    allow_nan=False,
                    sort_keys=True,
                    separators=(",", ":"),
                )
            )
        text = "\n".join(records) + ("\n" if records else "")
        return self._write(run_id, node, name, text, "jsonl")

    def append_jsonl(
        self,
        run_id: str,
        node: WorkflowNode,
        name: str,
        value: dict[str, Any],
    ) -> Any:
        if type(value) is not dict:
            raise ArtifactError("JSONL records must be objects")
        rendered = _canonical_json_object(_redacted_json(value))
        with self._lock:
            target = self._target(run_id, node, name)
            try:
                existing = target.read_text(encoding="utf-8") if target.exists() else ""
            except (OSError, UnicodeError):
                raise ArtifactError("existing JSONL artifact cannot be read") from None
            records: list[str] = []
            for line in existing.splitlines():
                if not line.strip():
                    continue
                parsed = _strict_json_object(line)
                records.append(_canonical_json_object(_redacted_json(parsed)))
            records.append(rendered)
            return self._write(
                run_id, node, name, "\n".join(records) + "\n", "jsonl"
            )

    def write_markdown(
        self, run_id: str, node: WorkflowNode, name: str, value: str
    ) -> Any:
        return self._write(run_id, node, name, redact_text(value), "markdown")

    def read_json(self, artifact: Any) -> dict[str, Any]:
        try:
            path = Path(artifact.path)
            run_id = artifact.run_id
            node = artifact.node
            name = artifact.name
        except Exception:
            raise ArtifactError("artifact record has no valid path") from None
        _validate_run_id(run_id)
        if type(node) is not WorkflowNode:
            raise ArtifactError("artifact record has an invalid node")
        _validate_name(name)
        try:
            resolved = path.resolve(strict=True)
        except OSError:
            raise ArtifactError("artifact path cannot be resolved") from None
        if not resolved.is_relative_to(self.root):
            raise ArtifactError("artifact path is outside the writer root")
        expected = (self.root / run_id / NODE_DIRECTORIES[node] / Path(name)).resolve(
            strict=False
        )
        if resolved != expected:
            raise ArtifactError("artifact path does not match its registry identity")
        try:
            content = resolved.read_bytes()
        except OSError:
            raise ArtifactError("artifact file cannot be read") from None
        expected = getattr(artifact, "sha256", None)
        if (
            type(expected) is not str
            or re.fullmatch(r"[0-9a-fA-F]{64}", expected) is None
        ):
            raise ArtifactError("artifact registry hash is invalid")
        if hashlib.sha256(content).hexdigest() != expected.casefold():
            raise ArtifactError("artifact hash does not match its registry record")
        try:
            value = json.loads(
                content.decode("utf-8"),
                parse_constant=lambda constant: (_ for _ in ()).throw(
                    ValueError("non-finite number")
                ),
            )
        except (UnicodeDecodeError, json.JSONDecodeError, ValueError):
            raise ArtifactError("artifact is not valid UTF-8 JSON") from None
        if type(value) is not dict:
            raise ArtifactError("artifact JSON must be an object")
        return _redacted_json(value)
