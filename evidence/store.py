from __future__ import annotations

from dataclasses import asdict
import json
import os
from pathlib import Path
from typing import Iterable

from .budget import BalanceObservation, CostObservation
from .models import EvidenceRecord
from .provenance import canonical_json, verify_evidence_record


class EvidenceStoreError(RuntimeError):
    pass


class EvidenceStore:
    """Durable local store for external evidence and provider cost observations.

    The store lives under ``local/evidence`` by default, which is already ignored
    by the repository. Evidence records are immutable: saving the same evidence id
    with different content is rejected rather than overwritten.
    """

    def __init__(self, root: str | Path) -> None:
        self.root = Path(root)

    @property
    def records_root(self) -> Path:
        return self.root / "records"

    @property
    def cost_root(self) -> Path:
        return self.root / "costs"

    @property
    def runs_root(self) -> Path:
        return self.root / "runs"

    @property
    def balance_root(self) -> Path:
        return self.root / "balances"

    def save_record(self, record: EvidenceRecord) -> Path:
        ok, problems = verify_evidence_record(record)
        if not ok:
            raise EvidenceStoreError(f"refusing invalid evidence record: {', '.join(problems)}")

        target = self.records_root / record.provider / f"{record.evidence_id}.json"
        payload = canonical_json(record.to_dict()) + "\n"
        if target.exists():
            existing = target.read_text(encoding="utf-8")
            if existing != payload:
                raise EvidenceStoreError(
                    f"immutable evidence collision for {record.evidence_id}"
                )
            return target

        _atomic_write_text(target, payload)
        index = self.records_root / record.provider / "index.jsonl"
        _append_jsonl(
            index,
            {
                "evidence_id": record.evidence_id,
                "provider": record.provider,
                "query_type": record.query_type,
                "retrieved_at": record.retrieved_at,
                "raw_sha256": record.raw_sha256,
                "provider_contract_version": record.provider_contract_version,
                "path": target.name,
            },
        )
        return target

    def load_record(self, provider: str, evidence_id: str) -> EvidenceRecord:
        path = self.records_root / provider / f"{evidence_id}.json"
        if not path.exists():
            raise FileNotFoundError(path)
        record = EvidenceRecord.from_dict(json.loads(path.read_text(encoding="utf-8")))
        ok, problems = verify_evidence_record(record)
        if not ok:
            raise EvidenceStoreError(
                f"stored evidence failed verification: {', '.join(problems)}"
            )
        return record

    def append_balance(self, observation: BalanceObservation) -> Path:
        path = self.balance_root / f"{observation.provider}.jsonl"
        _append_jsonl(
            path,
            {
                "provider": observation.provider,
                "available_points": observation.available_points,
                "observed_at": observation.observed_at,
                "source": observation.source,
            },
        )
        return path

    def load_balances(self, provider: str) -> list[BalanceObservation]:
        path = self.balance_root / f"{provider}.jsonl"
        if not path.exists():
            return []
        result: list[BalanceObservation] = []
        for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if not line.strip():
                continue
            try:
                payload = json.loads(line)
                result.append(
                    BalanceObservation(
                        provider=str(payload["provider"]),
                        available_points=float(payload["available_points"]),
                        observed_at=str(payload["observed_at"]),
                        source=str(payload["source"]),
                    )
                )
            except Exception as exc:
                raise EvidenceStoreError(
                    f"invalid balance ledger {path}:{line_number}: {exc}"
                ) from exc
        return result

    def latest_balance(self, provider: str) -> BalanceObservation | None:
        observations = self.load_balances(provider)
        return observations[-1] if observations else None

    def append_cost(self, provider: str, observation: CostObservation) -> Path:
        path = self.cost_root / f"{provider}.jsonl"
        _append_jsonl(
            path,
            {
                "query_type": observation.query_type,
                "points_before": observation.points_before,
                "points_after": observation.points_after,
                "success": observation.success,
                "timestamp": observation.timestamp,
                "cost": observation.cost,
            },
        )
        return path

    def load_costs(self, provider: str) -> list[CostObservation]:
        path = self.cost_root / f"{provider}.jsonl"
        if not path.exists():
            return []
        result: list[CostObservation] = []
        for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if not line.strip():
                continue
            try:
                payload = json.loads(line)
                result.append(
                    CostObservation(
                        query_type=str(payload["query_type"]),
                        points_before=float(payload["points_before"]),
                        points_after=float(payload["points_after"]),
                        success=bool(payload["success"]),
                        timestamp=str(payload["timestamp"]),
                    )
                )
            except Exception as exc:
                raise EvidenceStoreError(
                    f"invalid cost ledger {path}:{line_number}: {exc}"
                ) from exc
        return result

    def lock_provider_contract(
        self,
        *,
        run_id: str,
        provider: str,
        contract_version: str,
    ) -> Path:
        if not run_id.strip():
            raise ValueError("run_id must be non-empty")
        if not provider.strip() or not contract_version.strip():
            raise ValueError("provider and contract_version must be non-empty")
        target = self.runs_root / run_id / "provider-locks" / f"{provider}.json"
        payload = {
            "provider": provider,
            "contract_version": contract_version,
        }
        if target.exists():
            existing = json.loads(target.read_text(encoding="utf-8"))
            if existing != payload:
                raise EvidenceStoreError(
                    f"provider contract drift for run {run_id}: "
                    f"locked={existing.get('contract_version')} current={contract_version}"
                )
            return target
        _atomic_write_text(target, canonical_json(payload) + "\n")
        return target

    def read_provider_lock(self, *, run_id: str, provider: str) -> str | None:
        target = self.runs_root / run_id / "provider-locks" / f"{provider}.json"
        if not target.exists():
            return None
        payload = json.loads(target.read_text(encoding="utf-8"))
        return str(payload["contract_version"])

    def save_run_plan(self, *, run_id: str, plan_id: str, payload: dict[str, object]) -> Path:
        if not run_id.strip() or not plan_id.strip():
            raise ValueError("run_id and plan_id must be non-empty")
        target = self.runs_root / run_id / "plans" / f"{plan_id}.json"
        text = canonical_json(payload) + "\n"
        if target.exists():
            existing = target.read_text(encoding="utf-8")
            if existing != text:
                raise EvidenceStoreError(
                    f"immutable plan collision for run={run_id} plan={plan_id}"
                )
            return target
        _atomic_write_text(target, text)
        return target

    def append_run_event(
        self, *, run_id: str, plan_id: str, event: dict[str, object]
    ) -> Path:
        if not run_id.strip() or not plan_id.strip():
            raise ValueError("run_id and plan_id must be non-empty")
        path = self.runs_root / run_id / "journals" / f"{plan_id}.jsonl"
        _append_jsonl(path, event)
        return path

    def load_run_events(self, *, run_id: str, plan_id: str) -> list[dict[str, object]]:
        path = self.runs_root / run_id / "journals" / f"{plan_id}.jsonl"
        if not path.exists():
            return []
        events: list[dict[str, object]] = []
        for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if not line.strip():
                continue
            try:
                payload = json.loads(line)
                if not isinstance(payload, dict):
                    raise TypeError("event must be a JSON object")
                events.append(payload)
            except Exception as exc:
                raise EvidenceStoreError(
                    f"invalid run journal {path}:{line_number}: {exc}"
                ) from exc
        return events


def _atomic_write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.tmp-{os.getpid()}")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)


def _append_jsonl(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(canonical_json(payload))
        handle.write("\n")
