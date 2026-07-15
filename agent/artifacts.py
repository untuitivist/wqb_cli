from __future__ import annotations

import ast
import hashlib
import io
import json
import os
import re
import secrets
import stat
import threading
import tokenize
from contextlib import contextmanager
from dataclasses import dataclass
from math import isfinite
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Any, Iterable, Iterator

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


@dataclass(frozen=True)
class _ArtifactSnapshot:
    existed: bool
    content: bytes = b""
    mode: int = 0o600


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


def _contains_secret_json(value: Any) -> bool:
    if type(value) is dict:
        dynamic_secret = any(
            type(key) is str
            and key.strip().casefold() in {"key", "name", "type"}
            and type(child) is str
            and _is_secret_key(child)
            for key, child in value.items()
        )
        return any(
            _is_secret_key(key)
            or (dynamic_secret and key.strip().casefold() == "value")
            or _contains_secret_json(child)
            for key, child in value.items()
            if type(key) is str
        )
    if type(value) is list:
        return any(_contains_secret_json(child) for child in value)
    return False


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
    r"(?:(?P<equals>=)(?P<inline>\"(?:\\.|[^\"\\])*\"|'(?:\\.|[^'\\])*'|[^\s]+)"
    r"|\s+(?P<next>\"(?:\\.|[^\"\\])*\"|'(?:\\.|[^'\\])*'|[^\s]+))"
)


def _contains_secret_text(value: str) -> bool:
    for match in _TEXT_SECRET.finditer(value):
        if _is_secret_key(match.group("prefix").split(None, 1)[0].rstrip(":=")):
            return True
    for match in _QUOTED_OR_UNQUOTED_PAIR.finditer(value):
        if _is_secret_key(match.group("key")):
            return True
    for match in _CLI_PAIR.finditer(value):
        if _is_secret_key(match.group("flag").lstrip("-")):
            return True

    spans, unclosed_start = _scan_object_spans(value)
    for start, end in spans:
        candidate = value[start:end]
        try:
            parsed = _strict_json_object(candidate)
        except ArtifactError:
            try:
                parsed = _literal_eval_without_duplicate_keys(candidate)
            except Exception:
                if _has_dynamic_secret_shape(candidate):
                    return True
                continue
        if _contains_secret_json(parsed):
            return True
    return unclosed_start is not None and _has_dynamic_secret_shape(value[unclosed_start:])


def _snapshot_text_variants(content: bytes) -> tuple[str, ...]:
    variants = [content.decode("latin-1")]
    encodings: list[str] = []
    if content.startswith((b"\xff\xfe\x00\x00", b"\x00\x00\xfe\xff")):
        encodings.append("utf-32")
    elif content.startswith((b"\xff\xfe", b"\xfe\xff")):
        encodings.append("utf-16")
    else:
        sample = content[: min(len(content), 256)]
        if len(sample) >= 8 and len(sample) % 4 == 0:
            lanes = tuple(
                sum(byte == 0 for byte in sample[offset::4])
                for offset in range(4)
            )
            lane_size = len(sample) // 4
            if all(count * 4 >= lane_size * 3 for count in lanes[1:]):
                encodings.append("utf-32-le")
            elif all(count * 4 >= lane_size * 3 for count in lanes[:3]):
                encodings.append("utf-32-be")
        if len(sample) >= 4 and len(sample) % 2 == 0:
            even_zeros = sum(byte == 0 for byte in sample[::2])
            odd_zeros = sum(byte == 0 for byte in sample[1::2])
            lane_size = len(sample) // 2
            if odd_zeros * 4 >= lane_size * 3:
                encodings.append("utf-16-le")
            elif even_zeros * 4 >= lane_size * 3:
                encodings.append("utf-16-be")
    for encoding in encodings:
        try:
            variants.append(content.decode(encoding))
        except UnicodeDecodeError:
            raise ArtifactError("input snapshot has an unsupported text encoding") from None
    return tuple(variants)


def redact_text(value: str) -> str:
    if type(value) is not str:
        raise TypeError("text must be a string")

    result = _redact_embedded_objects(value)
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


def _strict_json_decoder() -> json.JSONDecoder:
    def object_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, child in pairs:
            if key in result:
                raise ValueError("duplicate object key")
            result[key] = child
        return result

    return json.JSONDecoder(
        object_pairs_hook=object_pairs,
        parse_constant=lambda constant: (_ for _ in ()).throw(
            ValueError("non-finite number")
        ),
    )


def _scan_object_spans(value: str) -> tuple[list[tuple[int, int]], int | None]:
    """Return complete outer object spans and the earliest unclosed object."""
    spans: list[tuple[int, int]] = []
    starts: list[int] = []
    quote: str | None = None
    escaped = False
    for index, character in enumerate(value):
        if not starts:
            if character == "{":
                starts.append(index)
            continue
        if quote is not None:
            if escaped:
                escaped = False
            elif character == "\\":
                escaped = True
            elif character == quote:
                quote = None
            continue
        if character in {"'", '"'}:
            quote = character
        elif character == "{":
            starts.append(index)
        elif character == "}" and starts:
            start = starts.pop()
            if not starts:
                spans.append((start, index + 1))
    return spans, starts[0] if starts else None


def _pair_string_value(raw: str) -> str | None:
    if raw[:1] in {"'", '"'} and raw[-1:] == raw[:1]:
        try:
            value = ast.literal_eval(raw)
        except Exception:
            return None
        return value if type(value) is str else None
    return raw


def _has_dynamic_secret_shape(candidate: str) -> bool:
    descriptors: list[str] = []
    has_value = False
    for match in _QUOTED_OR_UNQUOTED_PAIR.finditer(candidate):
        value = _pair_string_value(match.group("value"))
        if value is None:
            continue
        key = match.group("key").strip().casefold()
        if key in {"name", "type", "key"}:
            descriptors.append(value)
        elif key == "value":
            has_value = True
    if has_value and any(_is_secret_key(value) for value in descriptors):
        return True

    literal_strings: list[str] = []
    try:
        tokens = tokenize.generate_tokens(io.StringIO(candidate).readline)
        for token in tokens:
            if token.type != tokenize.STRING:
                continue
            try:
                value = ast.literal_eval(token.string)
            except Exception:
                continue
            if type(value) is str:
                literal_strings.append(value)
    except (IndentationError, SyntaxError, tokenize.TokenError):
        pass
    normalized = {value.strip().casefold() for value in literal_strings}
    return (
        bool(normalized & {"name", "type", "key"})
        and "value" in normalized
        and any(_is_secret_key(value) for value in literal_strings)
    )


def _literal_eval_without_duplicate_keys(candidate: str) -> Any:
    tree = ast.parse(candidate, mode="eval")
    for node in ast.walk(tree):
        if not isinstance(node, ast.Dict):
            continue
        keys: set[str] = set()
        for key_node in node.keys:
            if not isinstance(key_node, ast.Constant) or type(key_node.value) is not str:
                continue
            if key_node.value in keys:
                raise ValueError("duplicate literal object key")
            keys.add(key_node.value)
    return ast.literal_eval(tree)


def _redact_embedded_object(candidate: str) -> str:
    try:
        parsed = _strict_json_object(candidate)
    except ArtifactError:
        try:
            parsed = _literal_eval_without_duplicate_keys(candidate)
        except Exception:
            return "[REDACTED]" if _has_dynamic_secret_shape(candidate) else candidate
    if type(parsed) is not dict:
        return candidate
    try:
        return _canonical_json_object(_redacted_json(parsed))
    except Exception:
        return "[REDACTED]"


def _redact_embedded_objects(value: str) -> str:
    if len(value) > MAX_JSON_CHARS:
        return "[REDACTED]"
    spans, unclosed_start = _scan_object_spans(value)
    if unclosed_start is not None:
        spans = [span for span in spans if span[1] <= unclosed_start]

    output: list[str] = []
    cursor = 0
    for start, end in spans:
        output.append(value[cursor:start])
        output.append(_redact_embedded_object(value[start:end]))
        cursor = end
    if unclosed_start is None:
        output.append(value[cursor:])
        return "".join(output)

    output.append(value[cursor:unclosed_start])
    candidate = value[unclosed_start:]
    output.append("[REDACTED]" if _has_dynamic_secret_shape(candidate) else candidate)
    return "".join(output)


def _strict_json_object(text: str) -> dict[str, Any]:
    try:
        value, end = _strict_json_decoder().raw_decode(text)
    except (json.JSONDecodeError, ValueError):
        raise ArtifactError("text is not a strict JSON object") from None
    if text[end:].strip() or type(value) is not dict:
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

    def stage_input(
        self,
        run_id: str,
        node: WorkflowNode,
        content: bytes,
        sha256: str,
    ) -> Path:
        if type(content) is not bytes:
            raise TypeError("input snapshot content must be bytes")
        if (
            type(sha256) is not str
            or re.fullmatch(r"[0-9a-f]{64}", sha256) is None
            or hashlib.sha256(content).hexdigest() != sha256
        ):
            raise ArtifactError("input snapshot hash is invalid")
        if any(_contains_secret_text(text) for text in _snapshot_text_variants(content)):
            raise ArtifactError("input snapshot must not contain secret material")
        name = f".inputs/{sha256}-{len(content)}.bin"
        with self._lock:
            if os.name == "posix":
                if not self._supports_secure_dir_fd():
                    raise ArtifactError("secure dir_fd input snapshots are unavailable")
                return self._stage_input_with_dir_fd(
                    run_id, node, name, content, sha256
                )
            if os.name == "nt":
                return self._stage_input_with_windows_handles(
                    run_id, node, name, content, sha256
                )
            raise ArtifactError("secure input snapshots are unavailable")

    def verify_input_snapshot(self, path: Path, sha256: str, size: int) -> None:
        with self._lock:
            self._verify_input_snapshot(path, sha256, size)

    def _verify_input_snapshot(self, path: Path, sha256: str, size: int) -> None:
        if os.name == "posix":
            try:
                relative = path.absolute().relative_to(self.root)
            except ValueError:
                raise ArtifactError("input snapshot path is unsafe") from None
            self._verify_input_snapshot_with_dir_fd(relative, sha256, size)
            return
        descriptor: int | None = None
        try:
            resolved = path.resolve(strict=True)
            if not resolved.is_relative_to(self.root) or _is_link(path):
                raise ArtifactError("input snapshot path is unsafe")
            flags = os.O_RDONLY | getattr(os, "O_BINARY", 0)
            flags |= getattr(os, "O_NOFOLLOW", 0)
            descriptor = os.open(path, flags)
            if os.name == "nt" and self._final_path_for_fd(descriptor) != resolved:
                raise ArtifactError("input snapshot handle path changed")
            digest = hashlib.sha256()
            consumed = 0
            with os.fdopen(descriptor, "rb") as stream:
                descriptor = None
                before = os.fstat(stream.fileno())
                if not stat.S_ISREG(before.st_mode):
                    raise ArtifactError("input snapshot must be a regular file")
                while chunk := stream.read(1024 * 1024):
                    consumed += len(chunk)
                    if consumed > size:
                        raise ArtifactError("input snapshot size changed")
                    digest.update(chunk)
                after = os.fstat(stream.fileno())
            identity_before = (
                before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns
            )
            identity_after = (
                after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns
            )
            if (
                identity_before != identity_after
                or consumed != size
                or digest.hexdigest() != sha256
            ):
                raise ArtifactError("input snapshot content does not match its identity")
        except ArtifactError:
            raise
        except OSError:
            raise ArtifactError("input snapshot could not be verified") from None
        finally:
            if descriptor is not None:
                os.close(descriptor)

    def _verify_input_snapshot_with_dir_fd(
        self, relative: Path, sha256: str, size: int
    ) -> None:
        if relative.is_absolute() or not relative.parts:
            raise ArtifactError("input snapshot path is unsafe")
        parent_fd = self._open_parent_dir_fd(relative.parent.parts)
        descriptor: int | None = None
        try:
            flags = os.O_RDONLY | os.O_NOFOLLOW | getattr(os, "O_CLOEXEC", 0)
            descriptor = os.open(relative.name, flags, dir_fd=parent_fd)
            digest = hashlib.sha256()
            consumed = 0
            with os.fdopen(descriptor, "rb") as stream:
                descriptor = None
                before = os.fstat(stream.fileno())
                if not stat.S_ISREG(before.st_mode):
                    raise ArtifactError("input snapshot must be a regular file")
                while chunk := stream.read(1024 * 1024):
                    consumed += len(chunk)
                    if consumed > size:
                        raise ArtifactError("input snapshot size changed")
                    digest.update(chunk)
                after = os.fstat(stream.fileno())
            if (
                (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns)
                != (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns)
                or consumed != size
                or digest.hexdigest() != sha256
            ):
                raise ArtifactError("input snapshot content does not match its identity")
        except ArtifactError:
            raise
        except OSError:
            raise ArtifactError("input snapshot could not be verified") from None
        finally:
            if descriptor is not None:
                os.close(descriptor)
            os.close(parent_fd)

    def _stage_input_with_dir_fd(
        self,
        run_id: str,
        node: WorkflowNode,
        name: str,
        content: bytes,
        sha256: str,
    ) -> Path:
        relative = Path(run_id) / NODE_DIRECTORIES[node] / Path(name)
        parent_fd = self._open_parent_dir_fd(relative.parent.parts)
        temporary_name = f".{relative.name}.{secrets.token_hex(12)}.tmp"
        temporary_exists = False
        target = self.root / relative
        try:
            try:
                existing = os.stat(
                    relative.name, dir_fd=parent_fd, follow_symlinks=False
                )
            except FileNotFoundError:
                existing = None
            if existing is not None:
                if not stat.S_ISREG(existing.st_mode):
                    raise ArtifactError("input snapshot must be a regular file")
                self._verify_input_snapshot_with_dir_fd(relative, sha256, len(content))
                return target

            flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW
            flags |= getattr(os, "O_CLOEXEC", 0)
            descriptor = os.open(temporary_name, flags, 0o600, dir_fd=parent_fd)
            temporary_exists = True
            with os.fdopen(descriptor, "wb") as stream:
                stream.write(content)
                stream.flush()
                os.fsync(stream.fileno())
            try:
                os.link(
                    temporary_name,
                    relative.name,
                    src_dir_fd=parent_fd,
                    dst_dir_fd=parent_fd,
                    follow_symlinks=False,
                )
            except FileExistsError:
                self._verify_input_snapshot_with_dir_fd(relative, sha256, len(content))
                return target
            os.unlink(temporary_name, dir_fd=parent_fd)
            temporary_exists = False
            self._verify_input_snapshot_with_dir_fd(relative, sha256, len(content))
            descriptor = os.open(
                relative.name,
                os.O_RDONLY | os.O_NOFOLLOW | getattr(os, "O_CLOEXEC", 0),
                dir_fd=parent_fd,
            )
            try:
                os.fchmod(descriptor, stat.S_IREAD)
            finally:
                os.close(descriptor)
            os.fsync(parent_fd)
            return target
        except ArtifactError:
            raise
        except OSError:
            raise ArtifactError("input snapshot could not be staged securely") from None
        finally:
            if temporary_exists:
                try:
                    os.unlink(temporary_name, dir_fd=parent_fd)
                except OSError:
                    pass
            os.close(parent_fd)

    def _stage_input_with_windows_handles(
        self,
        run_id: str,
        node: WorkflowNode,
        name: str,
        content: bytes,
        sha256: str,
    ) -> Path:
        target = self._target(run_id, node, name)
        expected_parent = target.parent.resolve(strict=True)
        expected_target = expected_parent / target.name
        descriptor: int | None = None
        try:
            try:
                self._verify_input_snapshot(target, sha256, len(content))
                return target
            except ArtifactError:
                if target.exists():
                    raise
            flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_BINARY", 0)
            descriptor = os.open(target, flags, 0o600)
            if self._final_path_for_fd(descriptor) != expected_target:
                raise ArtifactError("input snapshot handle escaped its directory")
            with os.fdopen(descriptor, "wb") as stream:
                descriptor = None
                stream.write(content)
                stream.flush()
                os.fsync(stream.fileno())
            self._verify_input_snapshot(target, sha256, len(content))
            return target
        except ArtifactError:
            raise
        except OSError:
            raise ArtifactError("input snapshot could not be staged securely") from None
        finally:
            if descriptor is not None:
                os.close(descriptor)

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
                    try:
                        candidate.mkdir()
                    except FileExistsError:
                        if _is_link(candidate) or not candidate.is_dir():
                            raise ArtifactError(
                                "artifact parent must be a directory"
                            ) from None
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
        with self._lock, self._artifact_lock(run_id, node, name):
            return self._write_locked(run_id, node, name, text, kind)

    def _write_locked(
        self,
        run_id: str,
        node: WorkflowNode,
        name: str,
        text: str,
        kind: str,
    ) -> Any:
        snapshot = self._capture_target(run_id, node, name)
        if os.name == "posix":
            if not self._supports_secure_dir_fd():
                raise ArtifactError("secure dir_fd artifact writes are unavailable")
            target, digest = self._write_with_dir_fd(run_id, node, name, text)
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
            try:
                self._restore_target(run_id, node, name, snapshot, digest)
            except Exception:
                pass
            raise ArtifactError("artifact registry update failed") from None

    @contextmanager
    def _artifact_lock(
        self, run_id: str, node: WorkflowNode, name: str
    ) -> Iterator[None]:
        _validate_run_id(run_id)
        if type(node) is not WorkflowNode:
            raise ArtifactError("node must be a WorkflowNode")
        _validate_name(name)
        relative = Path(run_id) / NODE_DIRECTORIES[node] / Path(name)
        identity = os.path.normcase(os.path.normpath(str(relative))).encode("utf-8")
        lock_name = f"{hashlib.sha256(identity).hexdigest()}.lock"
        if os.name == "posix":
            with self._artifact_lock_with_dir_fd(lock_name):
                yield
            return
        if os.name == "nt":
            with self._artifact_lock_with_windows_handle(lock_name):
                yield
            return
        raise ArtifactError("secure artifact locking is unavailable")

    @contextmanager
    def _artifact_lock_with_dir_fd(self, lock_name: str) -> Iterator[None]:
        import fcntl

        parent_fd = self._open_parent_dir_fd((".artifact-locks",))
        descriptor: int | None = None
        locked = False
        try:
            flags = os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW
            flags |= getattr(os, "O_CLOEXEC", 0)
            descriptor = os.open(lock_name, flags, 0o600, dir_fd=parent_fd)
            if not stat.S_ISREG(os.fstat(descriptor).st_mode):
                raise ArtifactError("artifact lock must be a regular file")
            fcntl.flock(descriptor, fcntl.LOCK_EX)
            locked = True
            yield
        except ArtifactError:
            raise
        except OSError:
            if locked:
                raise
            raise ArtifactError("artifact lock could not be acquired securely") from None
        finally:
            if descriptor is not None:
                if locked:
                    try:
                        fcntl.flock(descriptor, fcntl.LOCK_UN)
                    except OSError:
                        pass
                os.close(descriptor)
            os.close(parent_fd)

    @contextmanager
    def _artifact_lock_with_windows_handle(self, lock_name: str) -> Iterator[None]:
        import msvcrt

        directory = self._ensure_directory(self.root / ".artifact-locks", create=True)
        expected_directory = directory.resolve(strict=True)
        lock_path = directory / lock_name
        descriptor: int | None = None
        locked = False
        try:
            if _is_link(lock_path):
                raise ArtifactError("artifact lock must not be a symbolic link")
            flags = os.O_RDWR | os.O_CREAT | getattr(os, "O_BINARY", 0)
            descriptor = os.open(lock_path, flags, 0o600)
            if self._final_path_for_fd(descriptor) != expected_directory / lock_name:
                raise ArtifactError("artifact lock handle escaped its directory")
            details = os.fstat(descriptor)
            if not stat.S_ISREG(details.st_mode):
                raise ArtifactError("artifact lock must be a regular file")
            if details.st_size == 0:
                os.write(descriptor, b"\0")
                os.fsync(descriptor)
            os.lseek(descriptor, 0, os.SEEK_SET)
            msvcrt.locking(descriptor, msvcrt.LK_LOCK, 1)
            locked = True
            yield
        except ArtifactError:
            raise
        except OSError:
            if locked:
                raise
            raise ArtifactError("artifact lock could not be acquired securely") from None
        finally:
            if descriptor is not None:
                if locked:
                    try:
                        os.lseek(descriptor, 0, os.SEEK_SET)
                        msvcrt.locking(descriptor, msvcrt.LK_UNLCK, 1)
                    except OSError:
                        pass
                os.close(descriptor)

    def _capture_target(
        self, run_id: str, node: WorkflowNode, name: str
    ) -> _ArtifactSnapshot:
        if os.name == "posix":
            if not self._supports_secure_dir_fd():
                raise ArtifactError("secure dir_fd artifact writes are unavailable")
            return self._capture_with_dir_fd(run_id, node, name)
        if os.name == "nt":
            return self._capture_with_windows_handle(run_id, node, name)
        raise ArtifactError("secure artifact writes are unavailable")

    def _restore_target(
        self,
        run_id: str,
        node: WorkflowNode,
        name: str,
        snapshot: _ArtifactSnapshot,
        expected_digest: str,
    ) -> None:
        current = self._capture_target(run_id, node, name)
        if (
            not current.existed
            or hashlib.sha256(current.content).hexdigest() != expected_digest
        ):
            raise ArtifactError("artifact changed before rollback")
        if os.name == "posix":
            self._restore_with_dir_fd(run_id, node, name, snapshot)
        elif os.name == "nt":
            self._restore_with_windows_handles(run_id, node, name, snapshot)
        else:
            raise ArtifactError("secure artifact rollback is unavailable")
        restored = self._capture_target(run_id, node, name)
        if snapshot.existed:
            if (
                not restored.existed
                or restored.content != snapshot.content
                or restored.mode != snapshot.mode
            ):
                raise ArtifactError("artifact rollback verification failed")
        elif restored.existed:
            raise ArtifactError("artifact rollback verification failed")

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

    def _open_windows_directory_handle(self, directory: Path, expected: Path) -> int:
        import ctypes
        import msvcrt
        from ctypes import wintypes

        create_file = ctypes.WinDLL("kernel32", use_last_error=True).CreateFileW
        create_file.argtypes = (
            wintypes.LPCWSTR,
            wintypes.DWORD,
            wintypes.DWORD,
            ctypes.c_void_p,
            wintypes.DWORD,
            wintypes.DWORD,
            wintypes.HANDLE,
        )
        create_file.restype = wintypes.HANDLE
        handle = create_file(
            str(directory),
            0x80000000 | 0x40000000,
            0x00000001 | 0x00000002 | 0x00000004,
            None,
            3,
            0x02000000 | 0x00200000,
            None,
        )
        if handle == wintypes.HANDLE(-1).value:
            raise ArtifactError("artifact directory cannot be opened securely")
        descriptor = msvcrt.open_osfhandle(handle, os.O_RDONLY | getattr(os, "O_BINARY", 0))
        try:
            if self._final_path_for_fd(descriptor) != expected:
                raise ArtifactError("artifact directory handle escaped its path")
            return descriptor
        except Exception:
            os.close(descriptor)
            raise

    def _open_windows_file_handle(
        self, path: Path, expected: Path, access: int
    ) -> int:
        import ctypes
        import msvcrt
        from ctypes import wintypes

        create_file = ctypes.WinDLL("kernel32", use_last_error=True).CreateFileW
        create_file.argtypes = (
            wintypes.LPCWSTR,
            wintypes.DWORD,
            wintypes.DWORD,
            ctypes.c_void_p,
            wintypes.DWORD,
            wintypes.DWORD,
            wintypes.HANDLE,
        )
        create_file.restype = wintypes.HANDLE
        handle = create_file(
            str(path), access, 0x00000001 | 0x00000002 | 0x00000004, None, 3, 0, None
        )
        if handle == wintypes.HANDLE(-1).value:
            if ctypes.get_last_error() in {2, 3}:
                raise FileNotFoundError(path)
            raise ArtifactError("artifact file cannot be opened securely")
        descriptor = msvcrt.open_osfhandle(handle, os.O_RDONLY | getattr(os, "O_BINARY", 0))
        try:
            if self._final_path_for_fd(descriptor) != expected:
                raise ArtifactError("artifact file handle escaped its path")
            return descriptor
        except Exception:
            os.close(descriptor)
            raise

    def _rename_windows_handle(
        self, descriptor: int, directory_descriptor: int, name: str
    ) -> None:
        import ctypes
        import msvcrt
        from ctypes import wintypes

        class _FileRenameInfo(ctypes.Structure):
            _fields_ = (
                ("replace", wintypes.BOOLEAN),
                ("root_directory", wintypes.HANDLE),
                ("name_length", wintypes.DWORD),
                ("name", wintypes.WCHAR * 1),
        )

        encoded = name.encode("utf-16-le")
        name_offset = _FileRenameInfo.name.offset
        buffer = ctypes.create_string_buffer(ctypes.sizeof(_FileRenameInfo) + len(encoded))
        info = _FileRenameInfo.from_buffer(buffer)
        info.replace = True
        info.root_directory = msvcrt.get_osfhandle(directory_descriptor)
        info.name_length = len(encoded)
        ctypes.memmove(ctypes.addressof(buffer) + name_offset, encoded, len(encoded))
        class _IoStatusBlock(ctypes.Structure):
            _fields_ = (("status", wintypes.LONG), ("information", ctypes.c_size_t))

        set_information = ctypes.WinDLL("ntdll").NtSetInformationFile
        set_information.argtypes = (
            wintypes.HANDLE,
            ctypes.POINTER(_IoStatusBlock),
            ctypes.c_void_p,
            wintypes.DWORD,
            wintypes.DWORD,
        )
        set_information.restype = wintypes.LONG
        status = set_information(
            msvcrt.get_osfhandle(descriptor),
            ctypes.byref(_IoStatusBlock()),
            buffer,
            len(buffer),
            10,
        )
        if status != 0:
            raise ArtifactError("artifact handle rename failed")

    def _unlink_windows_handle(self, descriptor: int) -> None:
        import ctypes
        import msvcrt
        from ctypes import wintypes

        delete = wintypes.BOOL(True)
        set_information = ctypes.WinDLL(
            "kernel32", use_last_error=True
        ).SetFileInformationByHandle
        set_information.argtypes = (
            wintypes.HANDLE,
            wintypes.DWORD,
            ctypes.c_void_p,
            wintypes.DWORD,
        )
        set_information.restype = wintypes.BOOL
        if not set_information(
            msvcrt.get_osfhandle(descriptor), 4, ctypes.byref(delete), ctypes.sizeof(delete)
        ):
            raise ArtifactError("artifact handle deletion failed")

    def _remove_windows_temporary(self, path: Path, expected: Path) -> None:
        descriptor: int | None = None
        try:
            descriptor = self._open_windows_file_handle(path, expected, 0x00010000)
            self._unlink_windows_handle(descriptor)
        except FileNotFoundError:
            return
        finally:
            if descriptor is not None:
                os.close(descriptor)

    def _write_with_windows_handles(
        self, run_id: str, node: WorkflowNode, name: str, text: str
    ) -> tuple[Path, str]:
        target = self._target(run_id, node, name)
        expected_parent = target.parent.resolve(strict=True)
        temporary = target.parent / f".{target.name}.{secrets.token_hex(12)}.tmp"
        descriptor: int | None = None
        directory_descriptor: int | None = None
        renamed = False
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
            descriptor = self._open_windows_file_handle(
                temporary,
                expected_parent / temporary.name,
                0x80000000 | 0x00010000,
            )
            directory_descriptor = self._open_windows_directory_handle(
                target.parent, expected_parent
            )
            self._rename_windows_handle(descriptor, directory_descriptor, target.name)
            renamed = True
            os.close(descriptor)
            descriptor = None
            os.close(directory_descriptor)
            directory_descriptor = None
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
            if directory_descriptor is not None:
                os.close(directory_descriptor)
            if not renamed:
                try:
                    self._remove_windows_temporary(
                        temporary, expected_parent / temporary.name
                    )
                except ArtifactError:
                    pass

    def _capture_with_windows_handle(
        self, run_id: str, node: WorkflowNode, name: str
    ) -> _ArtifactSnapshot:
        target = self._target(run_id, node, name)
        expected_parent = target.parent.resolve(strict=True)
        expected_target = expected_parent / target.name
        descriptor: int | None = None
        try:
            read_flags = os.O_RDONLY | getattr(os, "O_BINARY", 0)
            descriptor = os.open(target, read_flags)
            if self._final_path_for_fd(descriptor) != expected_target:
                raise ArtifactError("artifact target handle escaped its directory")
            chunks: list[bytes] = []
            with os.fdopen(descriptor, "rb") as stream:
                descriptor = None
                before = os.fstat(stream.fileno())
                if not stat.S_ISREG(before.st_mode):
                    raise ArtifactError("artifact target must be a regular file")
                while chunk := stream.read(1024 * 1024):
                    chunks.append(chunk)
                after = os.fstat(stream.fileno())
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
                raise ArtifactError("artifact target changed while it was read")
            return _ArtifactSnapshot(
                True, b"".join(chunks), stat.S_IMODE(before.st_mode)
            )
        except FileNotFoundError:
            return _ArtifactSnapshot(False)
        except ArtifactError:
            raise
        except OSError:
            raise ArtifactError("artifact target could not be captured securely") from None
        finally:
            if descriptor is not None:
                os.close(descriptor)

    def _restore_with_windows_handles(
        self,
        run_id: str,
        node: WorkflowNode,
        name: str,
        snapshot: _ArtifactSnapshot,
    ) -> None:
        target = self._target(run_id, node, name, create=False)
        expected_parent = target.parent.resolve(strict=True)
        expected_target = expected_parent / target.name
        if not snapshot.existed:
            descriptor: int | None = None
            try:
                descriptor = self._open_windows_file_handle(
                    target, expected_target, 0x00010000
                )
                if not stat.S_ISREG(os.fstat(descriptor).st_mode):
                    raise ArtifactError("artifact rollback target must be a regular file")
                self._unlink_windows_handle(descriptor)
                os.close(descriptor)
                descriptor = None
                return
            except FileNotFoundError:
                return
            finally:
                if descriptor is not None:
                    os.close(descriptor)

        temporary = target.parent / f".{target.name}.{secrets.token_hex(12)}.tmp"
        descriptor = None
        directory_descriptor: int | None = None
        renamed = False
        try:
            flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
            flags |= getattr(os, "O_BINARY", 0)
            descriptor = os.open(temporary, flags, 0o600)
            if self._final_path_for_fd(descriptor).parent != expected_parent:
                raise ArtifactError("artifact rollback temporary escaped its directory")
            with os.fdopen(descriptor, "wb") as stream:
                descriptor = None
                stream.write(snapshot.content)
                stream.flush()
                os.fchmod(stream.fileno(), snapshot.mode)
                os.fsync(stream.fileno())
            descriptor = self._open_windows_file_handle(
                temporary,
                expected_parent / temporary.name,
                0x80000000 | 0x00010000,
            )
            directory_descriptor = self._open_windows_directory_handle(
                target.parent, expected_parent
            )
            self._rename_windows_handle(descriptor, directory_descriptor, target.name)
            renamed = True
            os.close(descriptor)
            descriptor = None
            os.close(directory_descriptor)
            directory_descriptor = None
            descriptor = os.open(
                target, os.O_RDONLY | getattr(os, "O_BINARY", 0)
            )
            if self._final_path_for_fd(descriptor) != expected_target:
                raise ArtifactError("artifact rollback target escaped its directory")
            restored = os.fstat(descriptor)
            if stat.S_IMODE(restored.st_mode) != snapshot.mode:
                raise ArtifactError("artifact rollback mode could not be restored")
        finally:
            if descriptor is not None:
                os.close(descriptor)
            if directory_descriptor is not None:
                os.close(directory_descriptor)
            if not renamed:
                try:
                    self._remove_windows_temporary(
                        temporary, expected_parent / temporary.name
                    )
                except ArtifactError:
                    pass

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

    def _capture_with_dir_fd(
        self, run_id: str, node: WorkflowNode, name: str
    ) -> _ArtifactSnapshot:
        _validate_run_id(run_id)
        if type(node) is not WorkflowNode:
            raise ArtifactError("node must be a WorkflowNode")
        _validate_name(name)
        relative = Path(run_id) / NODE_DIRECTORIES[node] / Path(name)
        parent_fd = self._open_parent_dir_fd(relative.parent.parts)
        descriptor: int | None = None
        try:
            read_flags = os.O_RDONLY | os.O_NOFOLLOW
            read_flags |= getattr(os, "O_CLOEXEC", 0)
            descriptor = os.open(relative.name, read_flags, dir_fd=parent_fd)
            chunks: list[bytes] = []
            with os.fdopen(descriptor, "rb") as stream:
                descriptor = None
                before = os.fstat(stream.fileno())
                if not stat.S_ISREG(before.st_mode):
                    raise ArtifactError("artifact target must be a regular file")
                while chunk := stream.read(1024 * 1024):
                    chunks.append(chunk)
                after = os.fstat(stream.fileno())
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
                raise ArtifactError("artifact target changed while it was read")
            return _ArtifactSnapshot(
                True, b"".join(chunks), stat.S_IMODE(before.st_mode)
            )
        except FileNotFoundError:
            return _ArtifactSnapshot(False)
        except ArtifactError:
            raise
        except OSError:
            raise ArtifactError("artifact target could not be captured securely") from None
        finally:
            if descriptor is not None:
                os.close(descriptor)
            os.close(parent_fd)

    def _restore_with_dir_fd(
        self,
        run_id: str,
        node: WorkflowNode,
        name: str,
        snapshot: _ArtifactSnapshot,
    ) -> None:
        _validate_run_id(run_id)
        if type(node) is not WorkflowNode:
            raise ArtifactError("node must be a WorkflowNode")
        _validate_name(name)
        relative = Path(run_id) / NODE_DIRECTORIES[node] / Path(name)
        parent_fd = self._open_parent_dir_fd(relative.parent.parts)
        temporary_name = f".{relative.name}.{secrets.token_hex(12)}.tmp"
        temporary_exists = False
        try:
            if not snapshot.existed:
                try:
                    current = os.stat(
                        relative.name, dir_fd=parent_fd, follow_symlinks=False
                    )
                except FileNotFoundError:
                    return
                if not stat.S_ISREG(current.st_mode):
                    raise ArtifactError("artifact rollback target must be a regular file")
                os.unlink(relative.name, dir_fd=parent_fd)
                os.fsync(parent_fd)
                return

            flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW
            flags |= getattr(os, "O_CLOEXEC", 0)
            descriptor = os.open(temporary_name, flags, 0o600, dir_fd=parent_fd)
            temporary_exists = True
            with os.fdopen(descriptor, "wb") as stream:
                stream.write(snapshot.content)
                stream.flush()
                os.fchmod(stream.fileno(), snapshot.mode)
                os.fsync(stream.fileno())
            os.replace(
                temporary_name,
                relative.name,
                src_dir_fd=parent_fd,
                dst_dir_fd=parent_fd,
            )
            temporary_exists = False
            restored = os.stat(
                relative.name, dir_fd=parent_fd, follow_symlinks=False
            )
            if (
                not stat.S_ISREG(restored.st_mode)
                or stat.S_IMODE(restored.st_mode) != snapshot.mode
            ):
                raise ArtifactError("artifact rollback mode could not be restored")
            os.fsync(parent_fd)
        except ArtifactError:
            raise
        except OSError:
            raise ArtifactError("artifact could not be rolled back securely") from None
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
                    try:
                        os.mkdir(part, 0o700, dir_fd=current)
                    except FileExistsError:
                        pass
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
        with self._lock, self._artifact_lock(run_id, node, name):
            snapshot = self._capture_target(run_id, node, name)
            try:
                existing = snapshot.content.decode("utf-8") if snapshot.existed else ""
            except UnicodeDecodeError:
                raise ArtifactError("existing JSONL artifact cannot be read") from None
            records: list[str] = []
            for line in existing.splitlines():
                if not line.strip():
                    continue
                parsed = _strict_json_object(line)
                records.append(_canonical_json_object(_redacted_json(parsed)))
            records.append(rendered)
            return self._write_locked(
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
