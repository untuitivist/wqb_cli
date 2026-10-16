from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import uuid
from typing import Any, Mapping, Sequence

from ...models import EvidenceRecord
from .contract import WIND_PROVIDER_NAME, WIND_SERVER_TYPES, require_wind_access
from .normalize import WindResponseError, normalize_wind_evidence


class WindRuntimeError(RuntimeError):
    pass


class WindOutcomeUnknownError(WindRuntimeError):
    """A call may have reached Wind, but WQB lacks an authoritative terminal result."""



@dataclass(frozen=True)
class WindRuntimeStatus:
    available: bool
    skill_dir: str | None
    node_binary: str | None
    provider_contract_version: str | None
    reason: str


@dataclass(frozen=True)
class WindCallResult:
    record: EvidenceRecord
    raw_response: Any
    provider_contract_version: str


def default_wind_skill_candidates() -> tuple[Path, ...]:
    candidates: list[Path] = []
    env_dir = os.environ.get("WIND_MCP_SKILL_DIR")
    if env_dir:
        candidates.append(Path(env_dir).expanduser())
    cwd = Path.cwd()
    candidates.extend(
        [
            cwd / "skills" / "wind-mcp-skill",
            cwd / ".agents" / "skills" / "wind-mcp-skill",
            Path.home() / ".agents" / "skills" / "wind-mcp-skill",
            Path.home() / ".claude" / "skills" / "wind-mcp-skill",
        ]
    )
    seen: set[str] = set()
    result: list[Path] = []
    for item in candidates:
        resolved = item.resolve()
        key = str(resolved)
        if key not in seen:
            seen.add(key)
            result.append(resolved)
    return tuple(result)


def discover_wind_skill(explicit: str | Path | None = None) -> Path | None:
    candidates = (Path(explicit).expanduser().resolve(),) if explicit else default_wind_skill_candidates()
    for candidate in candidates:
        if (
            (candidate / "SKILL.md").is_file()
            and (candidate / "scripts" / "cli.mjs").is_file()
            and (candidate / "scripts" / "tool-manifest.json").is_file()
        ):
            return candidate
    return None


def wind_contract_fingerprint(skill_dir: str | Path) -> str:
    """Content fingerprint for the callable Wind contract.

    This intentionally avoids trusting an installation's Git metadata because
    global skill installers may not retain ``.git``. It fingerprints exactly the
    local routing/CLI/tool contract files whose drift could change a research run.
    """

    root = Path(skill_dir).resolve()
    required = [
        root / "SKILL.md",
        root / "scripts" / "cli.mjs",
        root / "scripts" / "tool-manifest.json",
    ]
    references = sorted((root / "references").glob("*.md")) if (root / "references").exists() else []
    files = [*required, *references]
    missing = [str(path) for path in required if not path.is_file()]
    if missing:
        raise WindRuntimeError(f"Wind skill contract files missing: {missing}")

    digest = hashlib.sha256()
    for path in files:
        rel = path.relative_to(root).as_posix().encode("utf-8")
        data = path.read_bytes()
        digest.update(len(rel).to_bytes(4, "big"))
        digest.update(rel)
        digest.update(len(data).to_bytes(8, "big"))
        digest.update(data)
    return f"wind-skill:sha256:{digest.hexdigest()}"


class WindRuntime:
    def __init__(
        self,
        *,
        skill_dir: str | Path | None = None,
        node_binary: str = "node",
        timeout_seconds: int = 120,
        expected_contract_version: str | None = None,
    ) -> None:
        self.skill_dir = discover_wind_skill(skill_dir)
        self.node_binary = node_binary
        self.timeout_seconds = timeout_seconds
        self.expected_contract_version = expected_contract_version

    def status(self) -> WindRuntimeStatus:
        if self.skill_dir is None:
            return WindRuntimeStatus(
                available=False,
                skill_dir=None,
                node_binary=shutil.which(self.node_binary),
                provider_contract_version=None,
                reason="wind_skill_not_found",
            )
        node = shutil.which(self.node_binary)
        if node is None:
            return WindRuntimeStatus(
                available=False,
                skill_dir=str(self.skill_dir),
                node_binary=None,
                provider_contract_version=None,
                reason="node_not_found",
            )
        version = wind_contract_fingerprint(self.skill_dir)
        if self.expected_contract_version and version != self.expected_contract_version:
            return WindRuntimeStatus(
                available=False,
                skill_dir=str(self.skill_dir),
                node_binary=node,
                provider_contract_version=version,
                reason="provider_contract_drift",
            )
        return WindRuntimeStatus(
            available=True,
            skill_dir=str(self.skill_dir),
            node_binary=node,
            provider_contract_version=version,
            reason="ready",
        )

    def call(
        self,
        *,
        node: str,
        purpose: str,
        server_type: str,
        tool_name: str,
        params: Mapping[str, Any],
        entity_ids: Mapping[str, str] | None = None,
        as_of: str | None = None,
        period: Mapping[str, str] | None = None,
        supports: Sequence[str] = (),
        limitations: Sequence[str] = (),
    ) -> WindCallResult:
        require_wind_access(node, purpose)
        if server_type not in WIND_SERVER_TYPES:
            raise WindRuntimeError(f"unsupported Wind server_type: {server_type}")
        status = self.status()
        if not status.available or self.skill_dir is None or status.provider_contract_version is None:
            raise WindRuntimeError(f"Wind runtime unavailable: {status.reason}")

        request_file = self.skill_dir / "scripts" / f"request-wqb-{uuid.uuid4().hex}.json"
        request_file.write_text(
            json.dumps(params, ensure_ascii=False, sort_keys=True),
            encoding="utf-8",
        )
        rel_request = f"@scripts/{request_file.name}"
        command = [
            self.node_binary,
            "scripts/cli.mjs",
            "call",
            server_type,
            tool_name,
            rel_request,
        ]
        try:
            completed = subprocess.run(
                command,
                cwd=self.skill_dir,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=self.timeout_seconds,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            raise WindOutcomeUnknownError(
                f"Wind call timed out after {self.timeout_seconds}s"
            ) from exc
        finally:
            try:
                request_file.unlink(missing_ok=True)
            except OSError:
                pass

        stdout = completed.stdout.strip()
        if not stdout:
            detail = completed.stderr.strip() or f"exit={completed.returncode}"
            raise WindOutcomeUnknownError(f"Wind CLI returned no JSON stdout: {detail}")
        try:
            raw_response = json.loads(stdout)
        except json.JSONDecodeError as exc:
            raise WindOutcomeUnknownError(
                f"Wind CLI stdout is not JSON (exit={completed.returncode}): {stdout[:500]}"
            ) from exc
        if not isinstance(raw_response, Mapping):
            raise WindRuntimeError("Wind CLI stdout JSON must be an object envelope")

        # Preserve authoritative Wind error semantics. Error envelopes are never
        # admitted as evidence, so provider drift cannot make them provenance-unsafe.
        if raw_response.get("ok") is False:
            normalize_wind_evidence(
                server_type=server_type,
                tool_name=tool_name,
                request=dict(params),
                raw_response=raw_response,
                provider_contract_version=status.provider_contract_version,
            )
            raise AssertionError("Wind error envelope unexpectedly normalized")

        post_contract_version = wind_contract_fingerprint(self.skill_dir)
        if post_contract_version != status.provider_contract_version:
            raise WindOutcomeUnknownError(
                "Wind provider contract changed during the call; result is not admitted as evidence"
            )

        # normalize_wind_evidence rejects route mismatch and attaches provenance.
        # mismatch, so a non-zero process exit can still produce the authoritative
        # provider error rather than being collapsed into a generic subprocess error.
        record = normalize_wind_evidence(
            server_type=server_type,
            tool_name=tool_name,
            request=dict(params),
            raw_response=raw_response,
            provider_contract_version=status.provider_contract_version,
            entity_ids=entity_ids,
            as_of=as_of,
            period=period,
            supports=supports,
            limitations=limitations,
        )
        if completed.returncode != 0:
            raise WindOutcomeUnknownError(
                f"Wind CLI returned exit={completed.returncode} despite a success envelope"
            )
        return WindCallResult(
            record=record,
            raw_response=raw_response,
            provider_contract_version=status.provider_contract_version,
        )
