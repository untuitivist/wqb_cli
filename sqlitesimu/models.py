from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


RUN_TERMINAL_STATES = {
    "COMPLETED",
    "COMPLETED_WITH_ERRORS",
    "BLOCKED",
    "CANCELLED",
}

EXPERIMENT_TERMINAL_STATES = {
    "READY",
    "PERMANENT_FAILURE",
    "SUBMIT_UNKNOWN",
    "CANCELLED",
}

ACTIVE_BATCH_STATES = {
    "SUBMITTING",
    "POLLING",
    "CHILD_POLLING",
}


@dataclass(frozen=True)
class CandidateSpec:
    payload: dict[str, Any]
    metadata: dict[str, Any] = field(default_factory=dict)
    priority: int = 0


@dataclass(frozen=True)
class SimulationManifest:
    name: str
    enrichment_profile: str
    candidates: tuple[CandidateSpec, ...]
    metadata: dict[str, Any] = field(default_factory=dict)
    requested_run_id: str | None = None


@dataclass(frozen=True)
class EnqueueResult:
    run_id: str
    accepted: int
    reused_candidates: int
    duplicates: int

    def as_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "accepted": self.accepted,
            "reused_candidates": self.reused_candidates,
            "duplicates": self.duplicates,
        }


@dataclass(frozen=True)
class RuntimePolicy:
    max_attempts: int = 5
    default_retry_seconds: float = 5.0
    idle_sleep_seconds: float = 1.0
    lease_seconds: float = 300.0


@dataclass(frozen=True)
class BatchRecord:
    id: str
    run_id: str
    state: str
    slot_class: str
    payload: Any
    attempts: int
    poll_attempts: int
    parent_simulation_id: str | None
    location: str | None


@dataclass(frozen=True)
class BatchItemRecord:
    batch_id: str
    experiment_id: str
    ordinal: int
    child_simulation_id: str | None
    alpha_id: str | None
    state: str
    attempts: int


@dataclass(frozen=True)
class ExperimentRecord:
    id: str
    run_id: str
    candidate_id: str
    state: str
    alpha_id: str | None
    attempts: int
