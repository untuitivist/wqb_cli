# WQB Multi-Model Quant Agent Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a resumable REGULAR FASTEXPR research agent that uses a high-capability Planner model for research decisions, a smaller Operator model for bounded execution preparation, deterministic `wqb` tooling for real platform actions, and a human approval gate for submission.

**Architecture:** Add a focused `agent/` package beneath the existing CLI. A deterministic coordinator owns the A-M state graph, budgets, validation, persistence, command allowlists, and approval; typed model adapters only return JSON decisions. SQLite stores durable state and structured experience, while raw artifacts stay under ignored `research_runs/`.

**Tech Stack:** Python 3.11, `argparse`, `dataclasses`, `sqlite3`, `requests`, `jsonschema`, keyring, `unittest`/pytest, existing `wqb_cli` commands. OpenAI requests use the Responses API with Structured Outputs; generic compatible endpoints use Chat Completions JSON Schema where supported.

**Design reference:** `docs/superpowers/specs/2026-07-15-wqb-quant-agent-design.md`

---

## File Map

New production files:

- `agent/__init__.py`: public agent package exports.
- `agent/types.py`: enums and immutable domain dataclasses.
- `agent/config.py`: agent/model configuration loading and validation.
- `agent/store.py`: SQLite schema, repositories, transitions, ledger, experience, approval.
- `agent/schemas.py`: JSON Schemas and typed model-response validation.
- `agent/models/base.py`: provider-neutral model request/result protocol.
- `agent/models/openai.py`: OpenAI Responses API adapter.
- `agent/models/compatible.py`: OpenAI-compatible Chat Completions adapter.
- `agent/models/router.py`: strict Planner/Operator routing and accounting.
- `agent/policy.py`: state, budget, role, command, and approval policies.
- `agent/context.py`: role-specific context manifests and evidence resolution.
- `agent/artifacts.py`: run directories, JSON/JSONL/Markdown artifact writes, redaction.
- `agent/runner.py`: idempotent subprocess command execution with node allowlists.
- `agent/expressions.py`: FASTEXPR normalization, fingerprinting, and static validation.
- `agent/nodes/discovery.py`: nodes A-D.
- `agent/nodes/evidence.py`: nodes F-G.
- `agent/nodes/research.py`: nodes H-I.
- `agent/nodes/evaluation.py`: nodes J-L.
- `agent/nodes/submission.py`: node M and approval subject validation.
- `agent/coordinator.py`: A-M orchestration, feedback loop, stop conditions, resume.
- `agent/reporting.py`: status, history, node summary, and final report projections.
- `agent/eval.py`: deterministic evaluation cases and metrics.
- `commands/agent.py`: `wqb agent` command tree and handlers.
- `skills/wqb-quant-agent/SKILL.md`: thin conversational wrapper around `wqb agent`.

Modified production files:

- `cli.py`: register and dispatch the `agent` command group.
- `core/config_store.py`: add agent defaults.
- `core/paths.py`: add agent database and run-root paths.
- `core/secrets.py`: expose role-specific secret lookup without logging values.
- `pyproject.toml`: add `jsonschema`, package the Skill, and bump the feature version.
- `README.md` and `README_CN.md`: setup, model roles, approval, recovery, and safety.
- `__init__.py`: keep the import version aligned with package metadata.

New tests:

- `tests/test_agent_types_config.py`
- `tests/test_agent_store.py`
- `tests/test_agent_schemas.py`
- `tests/test_agent_models.py`
- `tests/test_agent_policy_context.py`
- `tests/test_agent_runner.py`
- `tests/test_agent_expressions.py`
- `tests/test_agent_discovery_nodes.py`
- `tests/test_agent_evidence_research_nodes.py`
- `tests/test_agent_evaluation_nodes.py`
- `tests/test_agent_submission.py`
- `tests/test_agent_coordinator.py`
- `tests/test_agent_cli.py`
- `tests/test_agent_eval.py`

Test fixtures:

- `tests/fixtures/agent/authenticated.json`
- `tests/fixtures/agent/consultant_summary.json`
- `tests/fixtures/agent/pyramid_alphas.json`
- `tests/fixtures/agent/data_fields.json`
- `tests/fixtures/agent/community_search.json`
- `tests/fixtures/agent/simulation_complete.json`
- `tests/fixtures/agent/alpha_pass.json`
- `tests/fixtures/agent/alpha_fail.json`
- `tests/fixtures/agent/alpha_report_pass.json`

---

### Task 1: Domain Types, Paths, and Agent Configuration

**Files:**
- Create: `agent/__init__.py`
- Create: `agent/types.py`
- Create: `agent/config.py`
- Modify: `core/config_store.py`
- Modify: `core/paths.py`
- Modify: `pyproject.toml`
- Test: `tests/test_agent_types_config.py`

- [ ] **Step 1: Write failing tests for run configuration and role models**

```python
from pathlib import Path
import unittest

from wqb_cli.agent.config import load_agent_config
from wqb_cli.agent.types import ModelRole, RunConfig, ScopeMode


class AgentTypesConfigTests(unittest.TestCase):
    def test_manual_scope_requires_all_scope_fields(self) -> None:
        with self.assertRaisesRegex(ValueError, "manual scope requires"):
            RunConfig.from_dict({"scope_mode": "manual", "region": "USA"})

    def test_auto_scope_rejects_partial_manual_scope(self) -> None:
        with self.assertRaisesRegex(ValueError, "auto scope must not pin"):
            RunConfig.from_dict({"scope_mode": "auto", "region": "USA"})

    def test_agent_config_has_independent_model_roles(self) -> None:
        config = load_agent_config(None)
        self.assertEqual(config.models[ModelRole.PLANNER].api_style, "responses")
        self.assertEqual(config.models[ModelRole.OPERATOR].api_style, "chat_completions")
        self.assertEqual(config.default_budget.total_simulations, 40)
        self.assertEqual(config.run_root.name, "research_runs")

    def test_model_override_changes_only_model_id(self) -> None:
        config = load_agent_config(None)
        overridden = config.with_model_overrides(planner_model="planner-x", operator_model="operator-y")
        self.assertEqual(overridden.models[ModelRole.PLANNER].model, "planner-x")
        self.assertEqual(overridden.models[ModelRole.PLANNER].provider, config.models[ModelRole.PLANNER].provider)
        self.assertEqual(overridden.models[ModelRole.OPERATOR].model, "operator-y")
```

- [ ] **Step 2: Run the focused test and verify the missing package failure**

Run: `python -m pytest tests/test_agent_types_config.py -v`

Expected: FAIL with `ModuleNotFoundError: No module named 'wqb_cli.agent'`.

- [ ] **Step 3: Add immutable types and strict scope validation**

Create `agent/types.py` with these public types and values:

```python
from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class ModelRole(StrEnum):
    PLANNER = "planner"
    OPERATOR = "operator"


class ScopeMode(StrEnum):
    MANUAL = "manual"
    AUTO = "auto"


class RunState(StrEnum):
    CREATED = "CREATED"
    RUNNING = "RUNNING"
    NEEDS_AUTH = "NEEDS_AUTH"
    PAUSED_MODEL = "PAUSED_MODEL"
    AWAITING_APPROVAL = "AWAITING_APPROVAL"
    SUBMITTED = "SUBMITTED"
    REJECTED = "REJECTED"
    BUDGET_EXHAUSTED = "BUDGET_EXHAUSTED"
    NO_PROGRESS = "NO_PROGRESS"
    FAILED = "FAILED"


class WorkflowNode(StrEnum):
    A = "A"
    B = "B"
    C = "C"
    D = "D"
    F = "F"
    G = "G"
    H = "H"
    I = "I"
    J = "J"
    K = "K"
    L = "L"
    M = "M"


@dataclass(frozen=True)
class NodeResult:
    node: WorkflowNode
    summary: dict[str, Any]
    artifact_ids: tuple[str, ...] = ()
    next_node: WorkflowNode | None = None
    run_state: RunState | None = None
    payload: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class Budget:
    candidates_per_round: int = 8
    rounds: int = 5
    total_simulations: int = 40
    max_runtime_minutes: int = 180
    planner_calls: int = 20
    operator_calls: int = 100
    max_model_cost_usd: float | None = None


@dataclass(frozen=True)
class RunConfig:
    scope_mode: ScopeMode
    region: str | None = None
    delay: int | None = None
    universe: str | None = None
    neutralization: str | None = None
    budget: Budget = field(default_factory=Budget)

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "RunConfig":
        mode = ScopeMode(value["scope_mode"])
        scope = [value.get("region"), value.get("delay"), value.get("universe"), value.get("neutralization")]
        if mode is ScopeMode.MANUAL and any(item is None for item in scope):
            raise ValueError("manual scope requires region, delay, universe, and neutralization")
        if mode is ScopeMode.AUTO and any(item is not None for item in scope):
            raise ValueError("auto scope must not pin manual scope fields")
        return cls(
            scope_mode=mode,
            region=value.get("region"),
            delay=value.get("delay"),
            universe=value.get("universe"),
            neutralization=value.get("neutralization"),
            budget=Budget(**value.get("budget", {})),
        )
```

Create `agent/__init__.py` exporting `Budget`, `ModelRole`, `NodeResult`, `RunConfig`, `RunState`, `ScopeMode`, and `WorkflowNode`.

- [ ] **Step 4: Add path and configuration defaults**

Add to `core/paths.py`:

```python
DEFAULT_AGENT_DIR = LOCAL_ROOT / "agent"
DEFAULT_AGENT_SQLITE_PATH = DEFAULT_AGENT_DIR / "agent.sqlite3"
DEFAULT_RESEARCH_RUNS_ROOT = PACKAGE_ROOT / "research_runs"
```

Add an `agent` object to `DEFAULT_CONFIG` in `core/config_store.py` with exact defaults:

```python
"agent": {
    "database_path": "",
    "run_root": "",
    "models": {
        "planner": {
            "provider": "openai",
            "api_style": "responses",
            "model": "",
            "base_url": "https://api.openai.com/v1",
            "reasoning": "high",
            "secret_name": "agent-planner-api-key",
            "structured_outputs": True,
            "fallback_model": "",
            "input_cost_per_million": None,
            "output_cost_per_million": None,
        },
        "operator": {
            "provider": "openai-compatible",
            "api_style": "chat_completions",
            "model": "",
            "base_url": "",
            "reasoning": "",
            "secret_name": "agent-operator-api-key",
            "structured_outputs": True,
            "fallback_model": "",
            "input_cost_per_million": None,
            "output_cost_per_million": None,
        },
    },
    "budget": {
        "candidates_per_round": 8,
        "rounds": 5,
        "total_simulations": 40,
        "max_runtime_minutes": 180,
        "planner_calls": 20,
        "operator_calls": 100,
        "max_model_cost_usd": None,
    },
},
```

Implement `ModelConfig`, `AgentConfig`, and `load_agent_config` in `agent/config.py`. Resolve blank database/run paths to `DEFAULT_AGENT_SQLITE_PATH` and `DEFAULT_RESEARCH_RUNS_ROOT`. Reject missing model IDs only when `require_models=True`, so `--help`, `status`, and offline tests work before model setup.

Add `"wqb_cli.agent"` to `[tool.setuptools].packages`, then run `python -m pip install -e .` so the new package is available through the repository's editable-install workflow.

- [ ] **Step 5: Run the tests and commit**

Run: `python -m pytest tests/test_agent_types_config.py tests/test_cli_smoke.py -v`

Expected: PASS.

```powershell
git add agent core/config_store.py core/paths.py pyproject.toml tests/test_agent_types_config.py
git commit -m "feat(agent): add domain types and configuration"
```

---

### Task 2: Durable Run Store and State Transitions

**Files:**
- Create: `agent/store.py`
- Test: `tests/test_agent_store.py`

- [ ] **Step 1: Write failing store tests**

```python
import tempfile
import unittest
from pathlib import Path

from wqb_cli.agent.store import AgentStore, InvalidTransition
from wqb_cli.agent.types import RunConfig, RunState, WorkflowNode


class AgentStoreTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.store = AgentStore(Path(self.temp.name) / "agent.sqlite3")
        self.store.initialize()

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_create_run_persists_immutable_config(self) -> None:
        config = RunConfig.from_dict({
            "scope_mode": "manual", "region": "USA", "delay": 1,
            "universe": "TOP3000", "neutralization": "SUBINDUSTRY",
        })
        run = self.store.create_run("run-fixed", config)
        self.assertEqual(run.state, RunState.CREATED)
        self.assertEqual(self.store.get_run("run-fixed").config.region, "USA")

    def test_invalid_terminal_transition_fails_closed(self) -> None:
        config = RunConfig.from_dict({"scope_mode": "auto"})
        self.store.create_run("run-fixed", config)
        with self.assertRaises(InvalidTransition):
            self.store.transition("run-fixed", RunState.SUBMITTED, reason="skip approval")

    def test_node_attempts_keep_feedback_history(self) -> None:
        config = RunConfig.from_dict({"scope_mode": "auto"})
        self.store.create_run("run-fixed", config)
        first = self.store.start_node_attempt("run-fixed", WorkflowNode.I)
        self.store.finish_node_attempt(first, "COMPLETED", {"candidates": 8})
        second = self.store.start_node_attempt("run-fixed", WorkflowNode.I)
        self.assertEqual(second.attempt_number, 2)
```

- [ ] **Step 2: Run the test and verify the missing store failure**

Run: `python -m pytest tests/test_agent_store.py -v`

Expected: FAIL because `wqb_cli.agent.store` does not exist.

- [ ] **Step 3: Create the schema and transaction boundary**

Implement `AgentStore.initialize()` with SQLite foreign keys and WAL mode. The initial migration creates `schema_version`, `runs`, `state_transitions`, and `node_attempts`. Store immutable run configuration as canonical JSON and expose typed `RunRecord` and `NodeAttemptRecord` dataclasses.

```python
@dataclass(frozen=True)
class RunRecord:
    run_id: str
    state: RunState
    config: RunConfig

@dataclass(frozen=True)
class NodeAttemptRecord:
    id: int
    run_id: str
    node: WorkflowNode
    attempt_number: int
    status: str
```

Use this transition table in `agent/store.py`:

```python
ALLOWED_TRANSITIONS = {
    RunState.CREATED: {RunState.RUNNING, RunState.FAILED},
    RunState.RUNNING: {
        RunState.NEEDS_AUTH, RunState.PAUSED_MODEL, RunState.AWAITING_APPROVAL,
        RunState.BUDGET_EXHAUSTED, RunState.NO_PROGRESS, RunState.FAILED,
    },
    RunState.NEEDS_AUTH: {RunState.RUNNING, RunState.FAILED},
    RunState.PAUSED_MODEL: {RunState.RUNNING, RunState.FAILED},
    RunState.AWAITING_APPROVAL: {RunState.RUNNING, RunState.REJECTED, RunState.FAILED},
    RunState.SUBMITTED: set(),
    RunState.REJECTED: set(),
    RunState.BUDGET_EXHAUSTED: set(),
    RunState.NO_PROGRESS: set(),
    RunState.FAILED: set(),
}
```

Submission is intentionally absent here: only Task 12's approval transaction may move `AWAITING_APPROVAL -> RUNNING -> SUBMITTED`. `transition()` rejects that direct terminal hop.

- [ ] **Step 4: Implement run and node APIs**

Expose these concrete methods:

```python
def _canonical_json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))

def _now() -> str:
    return datetime.now(timezone.utc).isoformat()

def create_run(self, run_id: str, config: RunConfig) -> RunRecord:
    now = _now()
    with self.connect() as connection:
        connection.execute(
            "INSERT INTO runs(run_id, state, config_json, created_at, updated_at) VALUES(?,?,?,?,?)",
            (run_id, RunState.CREATED, _canonical_json(asdict(config)), now, now),
        )
    return self.get_run(run_id)

def get_run(self, run_id: str) -> RunRecord:
    row = self.connect().execute("SELECT * FROM runs WHERE run_id = ?", (run_id,)).fetchone()
    if row is None:
        raise KeyError(run_id)
    config = RunConfig.from_dict(json.loads(row["config_json"]))
    return RunRecord(run_id=row["run_id"], state=RunState(row["state"]), config=config)

def transition(self, run_id: str, target: RunState, *, reason: str) -> RunRecord:
    current = self.get_run(run_id)
    if target not in ALLOWED_TRANSITIONS[current.state]:
        raise InvalidTransition(f"{current.state} -> {target}")
    with self.connect() as connection:
        connection.execute("UPDATE runs SET state = ?, updated_at = ? WHERE run_id = ?", (target, _now(), run_id))
        connection.execute(
            "INSERT INTO state_transitions(run_id, from_state, to_state, reason, created_at) VALUES(?,?,?,?,?)",
            (run_id, current.state, target, reason, _now()),
        )
    return self.get_run(run_id)

def start_node_attempt(self, run_id: str, node: WorkflowNode) -> NodeAttemptRecord:
    row = self.connect().execute(
        "SELECT COALESCE(MAX(attempt_number), 0) AS n FROM node_attempts WHERE run_id = ? AND node = ?",
        (run_id, node),
    ).fetchone()
    number = int(row["n"]) + 1
    with self.connect() as connection:
        cursor = connection.execute(
            "INSERT INTO node_attempts(run_id, node, attempt_number, status, started_at) VALUES(?,?,?,?,?)",
            (run_id, node, number, "RUNNING", _now()),
        )
    return NodeAttemptRecord(cursor.lastrowid, run_id, node, number, "RUNNING")

def finish_node_attempt(self, attempt: NodeAttemptRecord, status: str, summary: dict[str, object]) -> None:
    with self.connect() as connection:
        connection.execute(
            "UPDATE node_attempts SET status = ?, summary_json = ?, finished_at = ? WHERE id = ?",
            (status, _canonical_json(summary), _now(), attempt.id),
        )

def latest_completed_node(self, run_id: str) -> WorkflowNode | None:
    row = self.connect().execute(
        "SELECT node FROM node_attempts WHERE run_id = ? AND status = 'COMPLETED' ORDER BY id DESC LIMIT 1",
        (run_id,),
    ).fetchone()
    return WorkflowNode(row["node"]) if row else None
```

Implement every write under `with self.connect() as connection:` so checkpoint and transition writes are atomic.

- [ ] **Step 5: Verify and commit**

Run: `python -m pytest tests/test_agent_store.py -v`

Expected: PASS.

```powershell
git add agent/store.py tests/test_agent_store.py
git commit -m "feat(agent): persist runs and node attempts"
```

---

### Task 3: Ledger, Plans, Usage, Experience, and Approval Records

**Files:**
- Modify: `agent/store.py`
- Test: `tests/test_agent_store.py`

- [ ] **Step 1: Add failing tests for idempotency and structured experience**

```python
def test_command_ledger_reuses_completed_fingerprint(self) -> None:
    config = RunConfig.from_dict({"scope_mode": "auto"})
    self.store.create_run("run-fixed", config)
    entry = self.store.reserve_command("run-fixed", "J", "sha256:abc", ["sim", "create"])
    self.store.complete_command(entry.id, exit_code=0, resource_id="SIM123", artifact_id="artifact-1")
    reused = self.store.reserve_command("run-fixed", "J", "sha256:abc", ["sim", "create"])
    self.assertEqual(reused.status, "COMPLETED")
    self.assertEqual(reused.resource_id, "SIM123")

def test_experience_search_filters_scope_and_failure_class(self) -> None:
    config = RunConfig.from_dict({"scope_mode": "auto"})
    self.store.create_run("run-fixed", config)
    self.store.add_experience("run-fixed", {
        "region": "USA", "delay": 1, "category": "PV",
        "field_ids": ["volume"], "failure_class": "EXPRESSION",
        "expression_fingerprint": "fp-1", "metrics": {"sharpe": 1.2},
    })
    hits = self.store.search_experience(region="USA", delay=1, category="PV", failure_class="EXPRESSION")
    self.assertEqual([item.expression_fingerprint for item in hits], ["fp-1"])

def test_approval_is_bound_to_alpha_and_report_hash(self) -> None:
    config = RunConfig.from_dict({"scope_mode": "auto"})
    self.store.create_run("run-fixed", config)
    approval = self.store.record_approval("run-fixed", "ALPHA1", "hash-a")
    self.assertTrue(self.store.approval_matches(approval.id, "run-fixed", "ALPHA1", "hash-a"))
    self.assertFalse(self.store.approval_matches(approval.id, "run-fixed", "ALPHA1", "hash-b"))
```

- [ ] **Step 2: Run only the new tests and observe missing methods**

Run: `python -m pytest tests/test_agent_store.py -v`

Expected: FAIL with missing `reserve_command`, `add_experience`, or `record_approval`.

- [ ] **Step 3: Extend the schema**

Add tables for `research_plans`, `operator_tasks`, `model_calls`, `command_ledger`, `artifacts`, `candidates`, `simulations`, `diagnoses`, `approvals`, `experiences`, and normalized `experience_fields`. Required uniqueness constraints:

```sql
UNIQUE(run_id, plan_version),
UNIQUE(run_id, task_id),
UNIQUE(run_id, command_fingerprint),
UNIQUE(run_id, expression_fingerprint),
UNIQUE(run_id, alpha_id, report_hash),
UNIQUE(experience_id, field_id)
```

Store JSON fields with `json.dumps(value, sort_keys=True, separators=(",", ":"))`. Add indexes on experience `(region, delay, category, failure_class)` and on ledger `(run_id, status)`.

- [ ] **Step 4: Implement repository methods with typed records**

Add APIs for versioned plans, task completion, model accounting, artifacts, ledger reservation/completion/failure, candidates, simulations, diagnoses, approvals, and experience queries. `add_experience` inserts the experience and all field IDs into `experience_fields` in one transaction. `reserve_command` must return the existing completed row without inserting a second row. An existing `STARTED` row must return status `RECOVERY_REQUIRED`, carrying the resource ID if already known.

Use an exact structured experience query:

```python
def search_experience(
    self, *, region: str, delay: int, category: str,
    field_id: str | None = None, failure_class: str | None = None, limit: int = 20,
) -> list[ExperienceRecord]:
    clauses = ["e.region = ?", "e.delay = ?", "e.category = ?"]
    values: list[object] = [region, delay, category]
    join = ""
    if field_id is not None:
        join = " JOIN experience_fields f ON f.experience_id = e.id"
        clauses.append("f.field_id = ?")
        values.append(field_id)
    if failure_class is not None:
        clauses.append("e.failure_class = ?")
        values.append(failure_class)
    query = "SELECT DISTINCT e.* FROM experiences e" + join + " WHERE " + " AND ".join(clauses) + " ORDER BY e.created_at DESC LIMIT ?"
    values.append(limit)
    return [self._experience_from_row(row) for row in self.connect().execute(query, values)]
```

- [ ] **Step 5: Verify migrations and commit**

Run: `python -m pytest tests/test_agent_store.py -v`

Expected: PASS, including reopening the database and calling `initialize()` twice.

```powershell
git add agent/store.py tests/test_agent_store.py
git commit -m "feat(agent): add ledger experience and approvals"
```

---

### Task 4: Model Schemas and Local Validation

**Files:**
- Create: `agent/schemas.py`
- Modify: `pyproject.toml`
- Test: `tests/test_agent_schemas.py`

- [ ] **Step 1: Write failing schema tests**

```python
import unittest

from wqb_cli.agent.schemas import SchemaViolation, validate_model_output
from wqb_cli.agent.types import ModelRole, WorkflowNode


class AgentSchemaTests(unittest.TestCase):
    def test_planner_k_accepts_only_bounded_route(self) -> None:
        value = {
            "decision": "revise_expression", "reasoning_summary": "Mechanism remains plausible",
            "evidence_refs": ["artifact:alpha-fail"], "confidence": 0.81,
            "diagnosis": {"failure_class": "EXPRESSION", "next_node": "I"},
        }
        self.assertEqual(validate_model_output(ModelRole.PLANNER, WorkflowNode.K, value)["diagnosis"]["next_node"], "I")

    def test_operator_cannot_return_route_or_budget(self) -> None:
        value = {
            "decision": "organized", "reasoning_summary": "Sorted metrics",
            "evidence_refs": ["artifact:sim-1"], "confidence": 0.9,
            "task_result": {"status": "COMPLETED", "payload": {}},
            "next_node": "H",
        }
        with self.assertRaises(SchemaViolation):
            validate_model_output(ModelRole.OPERATOR, WorkflowNode.K, value)

    def test_all_referenced_evidence_is_required(self) -> None:
        value = {"decision": "choose", "reasoning_summary": "No source", "evidence_refs": [], "confidence": 0.7}
        with self.assertRaisesRegex(SchemaViolation, "evidence_refs"):
            validate_model_output(ModelRole.PLANNER, WorkflowNode.D, value)
```

- [ ] **Step 2: Add `jsonschema` and verify the expected import failure**

Add `"jsonschema>=4.23"` to project dependencies and run `python -m pip install -e .`, then run:

Run: `python -m pytest tests/test_agent_schemas.py -v`

Expected: FAIL because `agent/schemas.py` does not exist.

- [ ] **Step 3: Define strict shared and node schemas**

Build schemas with `additionalProperties: false`. Every response requires:

```python
BASE_PROPERTIES = {
    "decision": {"type": "string", "minLength": 1},
    "reasoning_summary": {"type": "string", "minLength": 1},
    "evidence_refs": {"type": "array", "minItems": 1, "items": {"type": "string", "minLength": 1}},
    "confidence": {"type": "number", "minimum": 0, "maximum": 1},
}
```

Define exact node payloads: `scope_decision` for D, `evidence_requirements` for F/G, `research_plan` for H, `candidate_plan` or `task_result` for I, `diagnosis` for K, and `final_recommendation` for L. K's `failure_class/next_node` pairs must be checked after JSON Schema validation against:

```python
DIAGNOSIS_ROUTES = {
    "DATA_FIELD": "F",
    "EVIDENCE_GAP": "G",
    "ECONOMIC_MECHANISM": "H",
    "EXPRESSION": "I",
    "PASS": "L",
}
```

Expose `schema_for(role, node)` and `validate_model_output(role, node, value)`. Reject all Operator top-level keys outside the base keys and `task_result`.

- [ ] **Step 4: Add refusal and repair validation helpers**

Create `ModelRefusal` and `SchemaViolation` exceptions. `parse_json_text` must reject non-object JSON, strip no prose, and never attempt regex extraction from markdown fences. The adapter may retry twice with the original validation error; local validation remains authoritative even when a provider claims Structured Outputs.

- [ ] **Step 5: Verify and commit**

Run: `python -m pytest tests/test_agent_schemas.py -v`

Expected: PASS.

```powershell
git add agent/schemas.py tests/test_agent_schemas.py pyproject.toml
git commit -m "feat(agent): validate typed model decisions"
```

---

### Task 5: OpenAI, Compatible, and Strict Role Router

**Files:**
- Create: `agent/models/__init__.py`
- Create: `agent/models/base.py`
- Create: `agent/models/openai.py`
- Create: `agent/models/compatible.py`
- Create: `agent/models/router.py`
- Modify: `core/secrets.py`
- Modify: `pyproject.toml`
- Test: `tests/test_agent_models.py`

- [ ] **Step 1: Write failing adapter and routing tests**

```python
import unittest
from unittest.mock import Mock

from wqb_cli.agent.models.base import ModelRequest
from wqb_cli.agent.models.openai import OpenAIResponsesAdapter
from wqb_cli.agent.models.router import ModelRouter, RoleRoutingError
from wqb_cli.agent.types import ModelRole, WorkflowNode


class AgentModelTests(unittest.TestCase):
    def test_openai_adapter_uses_responses_structured_outputs(self) -> None:
        session = Mock()
        session.post.return_value = Mock(
            status_code=200,
            json=lambda: {
                "output": [{"type": "message", "content": [{"type": "output_text", "text": '{"decision":"x","reasoning_summary":"y","evidence_refs":["artifact:a"],"confidence":1}'}]}],
                "usage": {"input_tokens": 10, "output_tokens": 5},
            },
            raise_for_status=lambda: None,
        )
        adapter = OpenAIResponsesAdapter(session=session, api_key="secret", base_url="https://api.openai.com/v1", model="configured-model")
        adapter.invoke(ModelRequest(role=ModelRole.PLANNER, node=WorkflowNode.D, instructions="choose", context={}))
        body = session.post.call_args.kwargs["json"]
        self.assertEqual(body["text"]["format"]["type"], "json_schema")
        self.assertTrue(body["text"]["format"]["strict"]); self.assertNotIn("secret", str(body))

    def test_router_never_routes_planner_to_operator(self) -> None:
        planner = Mock(); operator = Mock()
        router = ModelRouter(planner=planner, operator=operator, store=Mock())
        router.invoke(ModelRequest(role=ModelRole.PLANNER, node=WorkflowNode.K, instructions="diagnose", context={}))
        planner.invoke.assert_called_once(); operator.invoke.assert_not_called()
        with self.assertRaises(RoleRoutingError):
            router.invoke(ModelRequest(role=ModelRole.OPERATOR, node=WorkflowNode.D, instructions="choose scope", context={}))
```

- [ ] **Step 2: Run tests and verify missing adapters**

Run: `python -m pytest tests/test_agent_models.py -v`

Expected: FAIL because `agent/models` does not exist.

- [ ] **Step 3: Implement provider-neutral request/result types**

Use these stable types in `agent/models/base.py`:

```python
@dataclass(frozen=True)
class ModelRequest:
    role: ModelRole
    node: WorkflowNode
    instructions: str
    context: dict[str, object]
    repair_error: str | None = None

@dataclass(frozen=True)
class ModelResult:
    value: dict[str, object]
    input_tokens: int | None
    output_tokens: int | None
    latency_ms: int
    provider_request_id: str | None

class ModelAdapter(Protocol):
    def invoke(self, request: ModelRequest) -> ModelResult:
        raise NotImplementedError
```

- [ ] **Step 4: Implement both HTTP adapters**

OpenAI request body follows the official Structured Outputs form:

```python
body = {
    "model": self.model,
    "instructions": request.instructions,
    "input": json.dumps(request.context, ensure_ascii=False),
    "text": {"format": {
        "type": "json_schema", "name": f"{request.role}_{request.node}",
        "strict": True, "schema": schema_for(request.role, request.node),
    }},
}
if self.reasoning:
    body["reasoning"] = {"effort": self.reasoning}
```

POST it to `{base_url}/responses` with Bearer auth, parse only `output[].content[]` items whose type is `output_text`, and detect `refusal`. The compatible adapter posts to `{base_url}/chat/completions`, sends system/user messages, and uses `response_format={"type": "json_schema", "json_schema": {"name": schema_name, "strict": True, "schema": schema_for(request.role, request.node)}}`. A role configuration may set `structured_outputs=false`; then compatible mode requests `json_object`, while local schema validation still applies.

Use `requests.Session`, a 60-second request timeout, at most two schema-repair calls, and bounded handling of HTTP 429/5xx. Never log headers or raw keys.

Add `"wqb_cli.agent.models"` to `[tool.setuptools].packages` when the package is created.

- [ ] **Step 5: Implement role routing, usage persistence, and secret lookup**

`ModelRouter` maps one adapter per role and checks node permissions before invoking. Planner is allowed at B, D, F, G, H, I, K, and L; Operator is allowed at B, F, G, H, I, K, and L. J and M allow no model. D and K are Planner-only decisions. Store each call through Task 3's `record_model_call`.

If an Operator `fallback_model` is configured, retry provider/network exhaustion once using that model through the same Operator adapter and record `fallback_used=true`. Reject Planner fallback configuration during config validation, and never route a Planner request to the Operator adapter. Compute call cost when both token counts and configured per-million rates are present; otherwise persist cost as null.

Add to `core/secrets.py`:

```python
def get_named_secret(secret_name: str, *, service: str = "wqb-cli") -> str | None:
    return get_secret(service, secret_name)
```

Configuration stores only `secret_name`; error messages may name the missing reference but never the value.

- [ ] **Step 6: Verify and commit**

Run: `python -m pytest tests/test_agent_models.py tests/test_agent_schemas.py -v`

Expected: PASS, with assertions that request logs and exceptions do not contain fake secrets.

```powershell
git add agent/models core/secrets.py pyproject.toml tests/test_agent_models.py
git commit -m "feat(agent): route planner and operator models"
```

---

### Task 6: Policy Engine and Role-Specific Context

**Files:**
- Create: `agent/policy.py`
- Create: `agent/context.py`
- Test: `tests/test_agent_policy_context.py`

- [ ] **Step 1: Write failing permission, budget, and context tests**

```python
import unittest

from wqb_cli.agent.context import ContextBuilder
from wqb_cli.agent.policy import AgentPolicy, PolicyViolation, UsageSnapshot
from wqb_cli.agent.types import Budget, ModelRole, WorkflowNode


class AgentPolicyContextTests(unittest.TestCase):
    def test_operator_cannot_change_plan_control_fields(self) -> None:
        policy = AgentPolicy(Budget())
        with self.assertRaisesRegex(PolicyViolation, "operator cannot modify"):
            policy.validate_operator_result({"task_result": {"status": "COMPLETED", "payload": {"budget": 80}}})

    def test_budget_blocks_next_simulation_at_limit(self) -> None:
        policy = AgentPolicy(Budget(total_simulations=2))
        with self.assertRaisesRegex(PolicyViolation, "simulation budget"):
            policy.require_simulation_capacity(UsageSnapshot(simulations=2, planner_calls=0, operator_calls=0, elapsed_minutes=1))

    def test_operator_context_excludes_other_tasks_and_secrets(self) -> None:
        builder = ContextBuilder(resolve_artifact=lambda ref: {"id": ref, "text": "safe"})
        context = builder.for_operator(
            task={"task_id": "task-1", "instruction": "organize"},
            plan={"version": 3, "scope": {"region": "USA"}, "tasks": [{"task_id": "task-1"}, {"task_id": "task-2"}]},
            evidence_refs=["artifact:a"],
        )
        self.assertEqual(context["task"]["task_id"], "task-1")
        self.assertNotIn("task-2", str(context)); self.assertNotIn("api_key", str(context).lower())
```

- [ ] **Step 2: Run tests and verify missing policy/context**

Run: `python -m pytest tests/test_agent_policy_context.py -v`

Expected: FAIL because the modules do not exist.

- [ ] **Step 3: Implement deterministic policies**

`AgentPolicy` must expose:

```python
@dataclass(frozen=True)
class UsageSnapshot:
    simulations: int
    planner_calls: int
    operator_calls: int
    elapsed_minutes: float
    rounds: int = 0
    model_cost_usd: float = 0.0

ROLE_NODES = {
    ModelRole.PLANNER: {WorkflowNode.B, WorkflowNode.D, WorkflowNode.F, WorkflowNode.G, WorkflowNode.H, WorkflowNode.I, WorkflowNode.K, WorkflowNode.L},
    ModelRole.OPERATOR: {WorkflowNode.B, WorkflowNode.F, WorkflowNode.G, WorkflowNode.H, WorkflowNode.I, WorkflowNode.K, WorkflowNode.L},
}
OPERATOR_CONTROL_KEYS = {"scope", "budget", "success_criteria", "next_node", "route", "plan_version", "submission"}

def _all_keys(value: object) -> set[str]:
    if isinstance(value, dict):
        return set(value) | set().union(*(_all_keys(child) for child in value.values()), set())
    if isinstance(value, list):
        return set().union(*(_all_keys(child) for child in value), set())
    return set()

def require_model_role(self, role: ModelRole, node: WorkflowNode) -> None:
    if node not in ROLE_NODES[role]:
        raise PolicyViolation(f"{role} is not allowed at node {node}")

def validate_operator_result(self, value: dict[str, object]) -> None:
    forbidden = _all_keys(value) & OPERATOR_CONTROL_KEYS
    if forbidden:
        raise PolicyViolation(f"operator cannot modify: {sorted(forbidden)}")

def require_simulation_capacity(self, usage: UsageSnapshot) -> None:
    if usage.simulations >= self.budget.total_simulations:
        raise PolicyViolation("simulation budget exhausted")

def stop_reason(self, usage: UsageSnapshot, consecutive_no_progress: int) -> str | None:
    cost_exhausted = self.budget.max_model_cost_usd is not None and usage.model_cost_usd >= self.budget.max_model_cost_usd
    if usage.rounds >= self.budget.rounds or usage.simulations >= self.budget.total_simulations or usage.planner_calls >= self.budget.planner_calls or usage.operator_calls >= self.budget.operator_calls or usage.elapsed_minutes >= self.budget.max_runtime_minutes or cost_exhausted:
        return "BUDGET_EXHAUSTED"
    return "NO_PROGRESS" if consecutive_no_progress >= 2 else None

def require_command(self, node: WorkflowNode, argv: tuple[str, ...]) -> None:
    if not any(argv[:len(prefix)] == prefix for prefix in self.command_allowlist[node]):
        raise PolicyViolation(f"command not allowed at node {node}: {argv[:2]}")

def require_submission_approval(self, *, run_state: RunState, approval_matches: bool) -> None:
    if run_state is not RunState.AWAITING_APPROVAL or not approval_matches:
        raise PolicyViolation("matching approval is required")
```

Reject Operator payload keys named `scope`, `budget`, `success_criteria`, `next_node`, `route`, `plan_version`, or `submission`. Return `BUDGET_EXHAUSTED` for any hard cap and `NO_PROGRESS` when the last two K cycles add no expression fingerprint.

- [ ] **Step 4: Implement context manifests and evidence resolution**

Planner context contains immutable run configuration, current plan, exact metrics, selected evidence, route history, and structured experience summaries. Operator context contains only one task, locked plan version/hash, required fields/operators, an output schema description, and explicitly referenced artifacts.

`ContextBuilder` must recursively redact keys matching `password`, `api_key`, `authorization`, `cookie`, `secret`, or `token`. It returns both the context dictionary and a `context_manifest` containing artifact/experience IDs; raw long documents remain outside the prompt until referenced.

- [ ] **Step 5: Verify and commit**

Run: `python -m pytest tests/test_agent_policy_context.py -v`

Expected: PASS.

```powershell
git add agent/policy.py agent/context.py tests/test_agent_policy_context.py
git commit -m "feat(agent): enforce policies and context isolation"
```

---

### Task 7: Artifact Writer and Idempotent Command Runner

**Files:**
- Create: `agent/artifacts.py`
- Create: `agent/runner.py`
- Test: `tests/test_agent_runner.py`

- [ ] **Step 1: Write failing runner tests**

```python
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from wqb_cli.agent.artifacts import ArtifactWriter
from wqb_cli.agent.policy import AgentPolicy, PolicyViolation
from wqb_cli.agent.runner import SubprocessCommandRunner
from wqb_cli.agent.types import Budget, WorkflowNode


class AgentRunnerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.writer = ArtifactWriter(Path(self.temp.name))
        self.store = Mock()
        self.policy = AgentPolicy(Budget())

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_disallowed_submit_is_rejected_outside_m(self) -> None:
        runner = SubprocessCommandRunner(self.store, self.policy, self.writer)
        with self.assertRaises(PolicyViolation):
            runner.run("run-1", WorkflowNode.J, ("alpha", "submit", "A1"), "bad.json")

    @patch("wqb_cli.agent.runner.subprocess.run")
    def test_completed_ledger_entry_is_reused(self, run: Mock) -> None:
        self.store.reserve_command.return_value = Mock(
            id=1, status="COMPLETED", resource_id="SIM1", artifact_id="artifact-1"
        )
        self.store.get_artifact.return_value = Mock(path=str(Path(self.temp.name) / "result.json"))
        Path(self.store.get_artifact.return_value.path).write_text('{"ok":true}', encoding="utf-8")
        result = SubprocessCommandRunner(self.store, self.policy, self.writer).run(
            "run-1", WorkflowNode.J, ("sim", "create", "--input", "batch.json"), "simulation.json"
        )
        self.assertTrue(result.reused); self.assertEqual(result.payload["ok"], True)
        run.assert_not_called()

    @patch("wqb_cli.agent.runner.subprocess.run")
    def test_started_simulation_with_resource_id_recovers_with_get(self, run: Mock) -> None:
        self.store.reserve_command.return_value = Mock(
            id=1, status="RECOVERY_REQUIRED", resource_id="SIM1", artifact_id=None
        )
        run.return_value = Mock(returncode=0, stdout='{"ok":true,"simulation_id":"SIM1"}', stderr="")
        SubprocessCommandRunner(self.store, self.policy, self.writer).run(
            "run-1", WorkflowNode.J, ("sim", "create", "--input", "batch.json"), "simulation.json"
        )
        executed = run.call_args.args[0]
        self.assertIn("get", executed); self.assertNotIn("create", executed)
```

- [ ] **Step 2: Run tests and verify missing writer/runner**

Run: `python -m pytest tests/test_agent_runner.py -v`

Expected: FAIL because `agent/artifacts.py` and `agent/runner.py` do not exist.

- [ ] **Step 3: Implement safe artifact writes**

`ArtifactWriter` creates `research_runs/<run_id>/<NN>_<node_name>/`, rejects `..` and absolute artifact names, writes UTF-8 through a temporary sibling plus `Path.replace`, and registers each artifact in the store. Implement:

```python
def _target(self, run_id: str, node: WorkflowNode, name: str) -> Path:
    relative = Path(name)
    if relative.is_absolute() or ".." in relative.parts:
        raise ValueError(f"unsafe artifact name: {name}")
    target = self.root / run_id / NODE_DIRECTORIES[node] / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    return target

def _replace_text(self, target: Path, text: str) -> None:
    temporary = target.with_suffix(target.suffix + ".tmp")
    temporary.write_text(text, encoding="utf-8")
    temporary.replace(target)

def write_json(self, run_id: str, node: WorkflowNode, name: str, value: object) -> ArtifactRecord:
    target = self._target(run_id, node, name)
    safe = redact(value)
    self._replace_text(target, json.dumps(safe, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
    return self.store.add_artifact(run_id, node, name, target, hashlib.sha256(target.read_bytes()).hexdigest())

def write_jsonl(self, run_id: str, node: WorkflowNode, name: str, value: dict[str, object]) -> ArtifactRecord:
    target = self._target(run_id, node, name)
    existing = target.read_text(encoding="utf-8") if target.exists() else ""
    line = json.dumps(redact(value), ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"
    self._replace_text(target, existing + line)
    return self.store.add_or_update_artifact(run_id, node, name, target, hashlib.sha256(target.read_bytes()).hexdigest())

def write_markdown(self, run_id: str, node: WorkflowNode, name: str, text: str) -> ArtifactRecord:
    target = self._target(run_id, node, name)
    self._replace_text(target, redact_text(text).rstrip() + "\n")
    return self.store.add_artifact(run_id, node, name, target, hashlib.sha256(target.read_bytes()).hexdigest())

def read_json(self, artifact: ArtifactRecord) -> dict[str, object]:
    value = json.loads(Path(artifact.path).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"artifact is not a JSON object: {artifact.id}")
    return value
```

Before writes, recursively redact the same secret keys defined in Task 6. `commands.jsonl` stores display-safe arguments: values following `--password`, `--api-key`, and `--secret` become `[REDACTED]`.

- [ ] **Step 4: Implement allowlisted subprocess execution and fingerprints**

Build the exact executable array without `shell=True`:

```python
command = [sys.executable, "-m", "wqb_cli", *argv]
completed = subprocess.run(
    command, cwd=PACKAGE_ROOT.parent, env=sanitized_environment(),
    text=True, encoding="utf-8", stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    timeout=timeout_seconds, check=False,
)
```

Normalize file arguments to content hashes before computing the command fingerprint, so moving the same input file does not bypass idempotency. Parse stdout as one JSON object; non-JSON stdout is a failed ledger entry. Record stdout payload as the requested artifact and stderr only after redaction.

For a `RECOVERY_REQUIRED` `sim create` row with `resource_id`, run `sim get RESOURCE_ID --max-wait-seconds 900`. For an uncertain `alpha submit`, do not POST; run `alpha get` and the submit status inspection path first. Do not add a generic retry for mutating commands.

- [ ] **Step 5: Define node command allowlists**

Use `(group, subcommand)` prefixes from the existing node documents. Important hard rules:

```python
NODE_COMMANDS = {
    WorkflowNode.A: {("auth", "status")},
    WorkflowNode.B: {("user", "consultant-summary"), ("user", "messages-summary"), ("user", "messages"), ("event", "list")},
    WorkflowNode.C: {("alpha", "list"), ("user", "alphas-summary"), ("user", "pyramid-alphas"), ("user", "pyramid-multipliers")},
    WorkflowNode.D: {("user", "consultant-summary"), ("user", "pyramid-alphas"), ("user", "pyramid-multipliers"), ("user", "user-diversity"), ("data", "categories")},
    WorkflowNode.F: {("scope", "files"), ("scope", "list"), ("scope", "show"), ("scope", "top"), ("scope", "alpha-rows"), ("data", "fields"), ("data", "datasets"), ("alpha", "list")},
    WorkflowNode.G: {("community", "search"), ("docs", "list"), ("docs", "show"), ("search",)},
    WorkflowNode.H: {("data", "field")},
    WorkflowNode.I: {("data", "operators"), ("data", "field"), ("docs", "show")},
    WorkflowNode.J: {("sim", "options"), ("sim", "create"), ("sim", "get"), ("alpha", "get"), ("alpha", "check"), ("alpha", "recordsets")},
    WorkflowNode.K: {("alpha", "get"), ("alpha", "check"), ("alpha", "pnl"), ("alpha", "yearly-stats"), ("alpha", "correlation", "self"), ("alpha", "correlation", "prod")},
    WorkflowNode.L: {("alpha", "get"), ("alpha", "check"), ("alpha", "correlation", "self"), ("alpha", "correlation", "prod"), ("alpha", "performance-comparison")},
    WorkflowNode.M: {("alpha", "submit"), ("alpha", "get")},
}
```

Maintain a separate external allowlist `{WorkflowNode.G: {("arxiv", "search", "query"), ("arxiv", "search", "raw")}}`. Permit it only when the executable resolves to the configured `arxiv_cli` entry point, and never through a shell.

- [ ] **Step 6: Verify and commit**

Run: `python -m pytest tests/test_agent_runner.py tests/test_agent_policy_context.py -v`

Expected: PASS.

```powershell
git add agent/artifacts.py agent/runner.py tests/test_agent_runner.py
git commit -m "feat(agent): add idempotent restricted command runner"
```

---

### Task 8: FASTEXPR Normalization and Static Validation

**Files:**
- Create: `agent/expressions.py`
- Test: `tests/test_agent_expressions.py`

- [ ] **Step 1: Write failing expression tests**

```python
import unittest

from wqb_cli.agent.expressions import ExpressionViolation, fingerprint_expression, validate_candidate


class AgentExpressionTests(unittest.TestCase):
    def test_whitespace_and_case_normalize_to_same_fingerprint(self) -> None:
        self.assertEqual(fingerprint_expression("TS_MEAN( volume , 20 )"), fingerprint_expression("ts_mean(volume,20)"))

    def test_string_literal_case_is_preserved(self) -> None:
        self.assertNotEqual(fingerprint_expression("ts_quantile(x,20,driver='Gaussian')"), fingerprint_expression("ts_quantile(x,20,driver='gaussian')"))

    def test_unknown_field_and_banned_field_are_rejected(self) -> None:
        candidate = {"expression": "rank(secret_field)", "field_id": "secret_field", "single_mechanism": True}
        with self.assertRaisesRegex(ExpressionViolation, "field"):
            validate_candidate(candidate, allowed_fields={"volume"}, banned_fields={"secret_field"}, operators={"rank": {"arity": 1}})

    def test_required_operator_parameters_are_enforced(self) -> None:
        candidate = {"expression": "ts_weighted_decay(volume)", "field_id": "volume", "single_mechanism": True}
        with self.assertRaisesRegex(ExpressionViolation, "k"):
            validate_candidate(candidate, allowed_fields={"volume"}, banned_fields=set(), operators={"ts_weighted_decay": {"arity": 1}})
```

- [ ] **Step 2: Run tests and verify the missing module**

Run: `python -m pytest tests/test_agent_expressions.py -v`

Expected: FAIL because `agent/expressions.py` does not exist.

- [ ] **Step 3: Implement a bounded tokenizer and canonical formatter**

Tokenize identifiers, numeric literals, single-quoted string literals, punctuation, and operators. Reject invalid characters, unterminated strings, and unbalanced parentheses. Lowercase identifiers and function names, preserve string contents, normalize numbers through `Decimal`, and remove insignificant whitespace. Hash the canonical UTF-8 form with SHA-256. Do not use regex substitution as the canonicalizer.

Expose:

```python
TOKEN = re.compile(
    r"(?P<space>\s+)|(?P<string>'(?:\\.|[^'\\])*')|"
    r"(?P<number>(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?)|"
    r"(?P<identifier>[A-Za-z_][A-Za-z0-9_.]*)|(?P<punct>[(),=+\-*/<>])"
)

def _normalized_number(text: str) -> str:
    value = Decimal(text)
    normalized = format(value.normalize(), "f")
    return "0" if normalized in {"-0", ""} else normalized

def normalize_expression(expression: str) -> str:
    position = 0
    depth = 0
    output: list[str] = []
    while position < len(expression):
        match = TOKEN.match(expression, position)
        if match is None:
            raise ExpressionViolation(f"invalid character at offset {position}")
        position = match.end()
        kind = match.lastgroup
        text = match.group()
        if kind == "space":
            continue
        if kind == "identifier":
            output.append(text.lower())
        elif kind == "number":
            output.append(_normalized_number(text))
        else:
            if text == "(":
                depth += 1
            elif text == ")":
                depth -= 1
                if depth < 0:
                    raise ExpressionViolation("unbalanced parentheses")
            output.append(text)
    if depth != 0:
        raise ExpressionViolation("unbalanced parentheses")
    if not output:
        raise ExpressionViolation("expression is empty")
    return "".join(output)

def fingerprint_expression(expression: str) -> str:
    return hashlib.sha256(normalize_expression(expression).encode("utf-8")).hexdigest()
```

- [ ] **Step 4: Implement candidate constraints**

Parse function calls sufficiently to count operators and fields and to inspect named arguments. Enforce at most five operator calls, at most two field IDs, `single_mechanism is True`, fields from the F allowlist, no fields from the banned set, and operators from current `wqb data operators` metadata. Enforce the explicit I-node parameters: `k`, `p`, `weight`, `lambda_min`, `lambda_max`, `target_tvr`, and polynomial `k` where required. Require `driver` to be a single-quoted literal for `ts_quantile`. Return a `ValidatedCandidate` containing canonical expression, fingerprint, fields, operators, and original candidate.

- [ ] **Step 5: Verify and commit**

Run: `python -m pytest tests/test_agent_expressions.py -v`

Expected: PASS.

```powershell
git add agent/expressions.py tests/test_agent_expressions.py
git commit -m "feat(agent): validate and deduplicate fastexpr candidates"
```

---

### Task 9: Discovery Nodes A-D

**Files:**
- Create: `agent/nodes/__init__.py`
- Create: `agent/nodes/discovery.py`
- Create: `tests/fixtures/agent/authenticated.json`
- Create: `tests/fixtures/agent/consultant_summary.json`
- Create: `tests/fixtures/agent/pyramid_alphas.json`
- Modify: `pyproject.toml`
- Test: `tests/test_agent_discovery_nodes.py`

- [ ] **Step 1: Add representative fixtures and failing tests**

The fixtures must preserve the real command envelope (`ok`, `request`, `response.status_code`, and `response.body`). Use fictional user/Alpha IDs and no credentials. Write tests:

```python
import unittest
from unittest.mock import Mock

from wqb_cli.agent.nodes.discovery import DiscoveryNodes
from wqb_cli.agent.types import RunConfig, RunState


class DiscoveryNodeTests(unittest.TestCase):
    def test_a_pauses_when_authentication_is_missing(self) -> None:
        runner = Mock(); runner.run.return_value.payload = {"ok": False, "response": {"status_code": 401}}
        result = DiscoveryNodes(runner=runner, router=Mock(), store=Mock()).run_a("run-1")
        self.assertEqual(result.run_state, RunState.NEEDS_AUTH)

    def test_manual_d_locks_market_scope_while_planner_selects_category(self) -> None:
        config = RunConfig.from_dict({"scope_mode": "manual", "region": "USA", "delay": 1, "universe": "TOP3000", "neutralization": "SUBINDUSTRY"})
        router = Mock(); router.invoke.return_value.value = {
            "decision": "choose tower", "reasoning_summary": "Unlit PV tower",
            "evidence_refs": ["artifact:quarter"], "confidence": 0.9,
            "scope_decision": {"candidate_id": "USA_D1_PV"},
        }
        candidates = {"quarter_towers": [{"candidate_id": "USA_D1_PV", "region": "USA", "delay": 1, "universe": "TOP3000", "neutralization": "SUBINDUSTRY", "category": "PV"}]}
        result = DiscoveryNodes(runner=Mock(), router=router, store=Mock()).run_d("run-1", config, candidates)
        self.assertEqual(result.scope["region"], "USA"); self.assertEqual(result.scope["category"], "PV")
        router.invoke.assert_called_once()

    def test_auto_d_uses_planner_only_after_validating_candidates(self) -> None:
        router = Mock(); router.invoke.return_value.value = {
            "decision": "choose tower", "reasoning_summary": "Closest unlit D1 tower",
            "evidence_refs": ["artifact:quarter"], "confidence": 0.9,
            "scope_decision": {"candidate_id": "USA_D1_PV"},
        }
        result = DiscoveryNodes(runner=Mock(), router=router, store=Mock()).run_d("run-1", RunConfig.from_dict({"scope_mode": "auto"}), {"quarter_towers": [{"candidate_id": "USA_D1_PV", "region": "USA", "delay": 1, "category": "PV"}]})
        self.assertEqual(result.scope["category"], "PV")
```

- [ ] **Step 2: Run tests and verify the missing node module**

Run: `python -m pytest tests/test_agent_discovery_nodes.py -v`

Expected: FAIL because `agent/nodes/discovery.py` does not exist.

- [ ] **Step 3: Implement A-C deterministic collection**

Use Runner calls from the existing A-C node documents. A never auto-reads or sends passwords: it checks `auth status` and returns `NEEDS_AUTH`; the user performs `wqb auth login`. B collects consultant summary, messages, announcements, and events, then asks Operator to organize active themes and Planner to rank opportunity relevance. C computes the current Eastern Time submission day with `zoneinfo.ZoneInfo("America/New_York")`, queries submitted Alpha records for that exact interval, and computes remaining REGULAR quota deterministically.

Every result returns a `NodeResult` with `node`, `summary`, `artifact_ids`, `next_node`, and optional `run_state`. Save the node files named in the existing workflow document.

Add `"wqb_cli.agent.nodes"` to `[tool.setuptools].packages` when `agent/nodes/__init__.py` is created.

- [ ] **Step 4: Implement locked manual scope and bounded automatic D**

Manual D validates the supplied market scope against `sim options`/platform metadata and filters current-quarter tower candidates to the locked `region`, `delay`, `universe`, and `neutralization`. Planner must select the category/main-tower candidate but cannot alter those four locked values. Automatic D builds candidates from current-quarter `pyramid-alphas --start-date --end-date` plus validated universe/neutralization options, calculates `neededToLight=max(0, 3-alphaCount)`, prioritizes D1 until D1 goals are satisfied, and passes candidate IDs to Planner. Reject a Planner response that selects an ID outside the supplied list. The resulting five-part scope, including category, is immutable for F-L.

- [ ] **Step 5: Verify and commit**

Run: `python -m pytest tests/test_agent_discovery_nodes.py tests/test_agent_models.py -v`

Expected: PASS.

```powershell
git add agent/nodes pyproject.toml tests/fixtures/agent tests/test_agent_discovery_nodes.py
git commit -m "feat(agent): implement discovery and scope selection nodes"
```

---

### Task 10: Evidence and Research Nodes F-I

**Files:**
- Create: `agent/nodes/evidence.py`
- Create: `agent/nodes/research.py`
- Create: `tests/fixtures/agent/data_fields.json`
- Create: `tests/fixtures/agent/community_search.json`
- Test: `tests/test_agent_evidence_research_nodes.py`

- [ ] **Step 1: Write failing F-I tests**

```python
import unittest

from wqb_cli.agent.nodes.evidence import evidence_coverage, screen_fields
from wqb_cli.agent.nodes.research import validate_mechanism_fields


class EvidenceResearchNodeTests(unittest.TestCase):
    def test_f_bans_fields_already_used_in_target_tower(self) -> None:
        result = screen_fields(
            platform_fields=[{"id": "volume", "dataset": {"id": "pv1"}}, {"id": "vwap", "dataset": {"id": "pv1"}}],
            used_fields={"volume"}, poor_os_fields=set(), used_datasets=set(),
        )
        self.assertIn("volume", result.banned_fields)
        self.assertEqual([field["id"] for field in result.candidate_fields], ["vwap"])

    def test_g_requires_four_evidence_classes(self) -> None:
        result = evidence_coverage([
            {"source_class": "community", "artifact_id": "a1"},
            {"source_class": "official_docs", "artifact_id": "a2"},
            {"source_class": "platform", "artifact_id": "a3"},
        ])
        self.assertFalse(result.complete)
        self.assertEqual(result.missing_sources, ("paper",))

    def test_h_cannot_add_field_outside_f_pool(self) -> None:
        with self.assertRaisesRegex(ValueError, "outside F candidate pool"):
            validate_mechanism_fields(
                {"mechanisms": [{"mechanism_id": "m1", "field_ids": ["secret_field"], "evidence_refs": ["artifact:a1"]}]},
                candidate_fields={"vwap"}, resolvable_evidence={"artifact:a1"},
            )

    def test_h_requires_resolvable_evidence(self) -> None:
        with self.assertRaisesRegex(ValueError, "evidence"):
            validate_mechanism_fields(
                {"mechanisms": [{"mechanism_id": "m1", "field_ids": ["vwap"], "evidence_refs": ["artifact:missing"]}]},
                candidate_fields={"vwap"}, resolvable_evidence={"artifact:a1"},
            )
```

- [ ] **Step 2: Run tests and verify missing evidence/research modules**

Run: `python -m pytest tests/test_agent_evidence_research_nodes.py -v`

Expected: FAIL because the new node modules do not exist.

- [ ] **Step 3: Implement F field screening and experience retrieval**

Execute `scope files/list/show/top`, platform field/dataset queries, tag-first active Alpha search, and paginated region/delay fallback exactly as specified in F's node document. If required `local/data_all` files are absent, return a typed `DATA_SOURCE_MISSING` failure with setup paths; do not ask a model to compensate. Parse target tower Alpha code to identify used fields, keeping base price/volume fields separately. Ban used fields and poor OS fields, then query Task 3's experience store for matching scope/category failures. Operator may organize results; Planner decides additional evidence requirements, but deterministic filters remain authoritative.

- [ ] **Step 4: Implement G source coverage**

For each selected mechanism keyword, persist actual results from local community, bundled docs, platform search, and `arxiv` when installed. If `arxiv` is unavailable or returns no valid paper, record `paper_source_unavailable` and return an evidence gap; do not fabricate citations. Evidence IDs use `artifact:<id>` and every lesson records source class, source ID, extracted statement, and applicability.

- [ ] **Step 5: Implement H Planner research plans**

Fetch field metadata for F candidates, combine the four G evidence classes, and ask Planner for a versioned `ResearchPlan`. Validate that every mechanism references a candidate field, current tower, and resolvable evidence. Store canonical plan JSON and SHA-256 hash. H must not produce expressions or settings.

- [ ] **Step 6: Implement I Planner/Operator split and static validation**

Planner creates `CandidatePlan` tasks containing mechanism ID, permitted fields, permitted transform families, and count. Operator materializes FASTEXPR only for one task at a time. Validate each response with Task 4, enforce locked plan version/hash with Task 6, validate expressions with Task 8, and reject fingerprints already present in the run or matching scope experience unless `allow_revalidation` is true. Persist accepted and rejected candidates with reasons.

- [ ] **Step 7: Verify and commit**

Run: `python -m pytest tests/test_agent_evidence_research_nodes.py tests/test_agent_expressions.py -v`

Expected: PASS.

```powershell
git add agent/nodes/evidence.py agent/nodes/research.py tests/fixtures/agent tests/test_agent_evidence_research_nodes.py
git commit -m "feat(agent): implement evidence and research nodes"
```

---

### Task 11: Simulation, Diagnosis, and Final-Check Nodes J-L

**Files:**
- Create: `agent/nodes/evaluation.py`
- Create: `tests/fixtures/agent/simulation_complete.json`
- Create: `tests/fixtures/agent/alpha_pass.json`
- Create: `tests/fixtures/agent/alpha_fail.json`
- Create: `tests/fixtures/agent/alpha_report_pass.json`
- Test: `tests/test_agent_evaluation_nodes.py`

- [ ] **Step 1: Write failing evaluation-node tests**

```python
import unittest

from wqb_cli.agent.nodes.evaluation import (
    classify_final_checks, classify_hard_metrics, extract_alpha_ids, select_passing_candidate,
)


class EvaluationNodeTests(unittest.TestCase):
    def test_hard_metrics_require_every_threshold_and_check(self) -> None:
        passing = {"sharpe": 1.59, "fitness": 1.01, "turnover": 0.02, "margin": 0.0011, "checks": [{"result": "PASS"}]}
        failing = {**passing, "checks": [{"result": "FAIL"}]}
        self.assertTrue(classify_hard_metrics(passing).passed)
        self.assertFalse(classify_hard_metrics(failing).passed)

    def test_j_records_real_alpha_id_not_child_simulation_id(self) -> None:
        payload = {"children": [{
            "simulation_id": "SIM-CHILD-1",
            "result": {"response": {"body": {"status": "COMPLETE", "alpha": "ALPHA123"}}},
        }]}
        self.assertEqual(extract_alpha_ids(payload), ("ALPHA123",))
        self.assertNotIn("SIM-CHILD-1", extract_alpha_ids(payload))

    def test_k_selects_passing_candidate_deterministically(self) -> None:
        candidates = [
            {"alpha_id": "A1", "sharpe": 1.7, "fitness": 1.1, "turnover": 0.3, "margin": 0.0011, "checks": [{"result": "PASS"}]},
            {"alpha_id": "A2", "sharpe": 1.9, "fitness": 1.2, "turnover": 0.2, "margin": 0.0013, "checks": [{"result": "PASS"}]},
        ]
        self.assertEqual(select_passing_candidate(candidates)["alpha_id"], "A2")

    def test_l_fails_when_correlation_or_platform_check_fails(self) -> None:
        report = {
            "check": {"checks": [{"result": "PASS"}]},
            "self_correlation": {"passed": True},
            "prod_correlation": {"passed": False},
            "performance_comparison": {"ok": True},
        }
        self.assertFalse(classify_final_checks(report).passed)
        self.assertIn("prod_correlation", classify_final_checks(report).failures)
```

- [ ] **Step 2: Run tests and verify missing evaluation nodes**

Run: `python -m pytest tests/test_agent_evaluation_nodes.py -v`

Expected: FAIL because `agent/nodes/evaluation.py` does not exist.

- [ ] **Step 3: Implement J batching and durable Simulation identity**

Construct REGULAR FASTEXPR multi-simulation bodies from validated candidates and the locked scope. Use `min(policy candidates_per round, 8)` per non-GLB batch and `min(policy candidates per round, 4)` for GLB, which keeps the agent below both its own default candidate budget and the existing external concurrency caps. Invoke `sim create` through Task 7, persist the parent/child Simulation IDs immediately when present, then extract real Alpha IDs from completed child response bodies and fetch Alpha/check/recordset data. A timeout with a recorded Simulation ID is recoverable, not a fresh create.

Use this return contract:

```python
@dataclass(frozen=True)
class SimulationBatchResult:
    simulation_ids: tuple[str, ...]
    alpha_results: tuple[dict[str, object], ...]
    new_fingerprints: tuple[str, ...]
    platform_failures: tuple[dict[str, object], ...]
```

- [ ] **Step 4: Implement deterministic hard metrics and Planner diagnosis**

`classify_hard_metrics` uses strict comparisons: Sharpe `>1.58`, Fitness `>1`, Turnover `>0.01 and <0.70`, Margin `>0.001`, and no check result equal to `FAIL`. Downrank or reject candidates without the visualization evidence required by the existing K node. If one or more candidates pass, select the deterministic ranking `(sharpe, fitness, margin, -abs(turnover-0.2))` and route to L without asking a model whether numeric thresholds passed.

When none pass, Operator organizes metrics, then Planner returns one valid Task 4 diagnosis. Validate the evidence IDs and exact failure-class route. Store diagnosis and `best_alpha_candidates.json`.

- [ ] **Step 5: Implement L slow checks**

For each selected candidate run Alpha get/check, self correlation, prod correlation, and performance comparison. Determine the final platform pass from the returned checks and correlation limit fields, preserving the complete raw records. Operator organizes these records; Planner produces the final recommendation and risk summary. L returns M only when deterministic checks pass; otherwise it returns K with an explicit failure record.

- [ ] **Step 6: Verify and commit**

Run: `python -m pytest tests/test_agent_evaluation_nodes.py tests/test_agent_runner.py -v`

Expected: PASS.

```powershell
git add agent/nodes/evaluation.py tests/fixtures/agent tests/test_agent_evaluation_nodes.py
git commit -m "feat(agent): implement simulation diagnosis and final checks"
```

---

### Task 12: Report Hash, Human Approval, and Submission Node M

**Files:**
- Create: `agent/reporting.py`
- Create: `agent/nodes/submission.py`
- Modify: `agent/store.py`
- Test: `tests/test_agent_submission.py`

- [ ] **Step 1: Write failing approval-gate tests**

```python
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock

from wqb_cli.agent.nodes.submission import ApprovalMismatch, SubmissionNode
from wqb_cli.agent.reporting import canonical_report_hash


class AgentSubmissionTests(unittest.TestCase):
    def test_report_hash_is_canonical(self) -> None:
        self.assertEqual(canonical_report_hash({"b": 2, "a": 1}), canonical_report_hash({"a": 1, "b": 2}))

    def test_m_never_submits_without_matching_approval(self) -> None:
        runner = Mock(); store = Mock(); store.find_unconsumed_approval.return_value = None
        with self.assertRaises(ApprovalMismatch):
            SubmissionNode(runner=runner, store=store).submit("run-1", "ALPHA1", {"final": True})
        runner.run.assert_not_called()

    def test_report_change_invalidates_approval(self) -> None:
        runner = Mock(); store = Mock(); store.find_unconsumed_approval.return_value = Mock(id=1, alpha_id="ALPHA1", report_hash="old")
        with self.assertRaises(ApprovalMismatch):
            SubmissionNode(runner=runner, store=store).submit("run-1", "ALPHA1", {"final": "changed"})
        runner.run.assert_not_called()

    def test_matching_approval_permits_one_submit(self) -> None:
        report = {"final": True}; report_hash = canonical_report_hash(report)
        runner = Mock(); runner.run.return_value.payload = {"ok": True, "submit_code": 200}
        store = Mock(); store.find_unconsumed_approval.return_value = Mock(id=1, alpha_id="ALPHA1", report_hash=report_hash)
        SubmissionNode(runner=runner, store=store).submit("run-1", "ALPHA1", report)
        runner.run.assert_called_once(); store.consume_approval_and_finish_submission.assert_called_once()
```

- [ ] **Step 2: Run tests and verify missing reporting/submission modules**

Run: `python -m pytest tests/test_agent_submission.py -v`

Expected: FAIL because the modules do not exist.

- [ ] **Step 3: Implement canonical final reports and approval subjects**

Build final report JSON from immutable run config, scope, plan version/hash, candidate metrics/checks, evidence references, route history, budgets, per-role usage, and terminal recommendation. Hash canonical UTF-8 JSON with SHA-256:

```python
def canonical_report_hash(report: dict[str, object]) -> str:
    encoded = json.dumps(report, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()
```

Write both `final_report.json` and a readable `final_report.md`. Approval always binds `run_id`, one recommended `alpha_id`, and this hash.

- [ ] **Step 4: Implement approval transaction and M**

Add store methods `record_approval`, `find_unconsumed_approval`, `record_rejection`, `begin_approved_submission`, and `consume_approval_and_finish_submission`. `begin_approved_submission` uses `BEGIN IMMEDIATE`, verifies state `AWAITING_APPROVAL`, exact Alpha/hash match, and `consumed_at IS NULL`, then changes state to RUNNING. `consume_approval_and_finish_submission` atomically marks the approval consumed, stores the submit result, and changes state to SUBMITTED.

`SubmissionNode.submit` performs no submit call before the transaction passes. Invoke `alpha submit` exactly once through Task 7; its internal waiting semantics remain the source of truth. Alpha metadata patching is outside the first version, so an approval cannot conceal an additional mutation. If submission status is uncertain, persist RUNNING/FAILED detail and require status inspection on resume instead of another POST. Rejection writes M's no-op report and ends as REJECTED. Budget/no-progress finalization also uses M in record-only mode and never creates an approval.

- [ ] **Step 5: Verify and commit**

Run: `python -m pytest tests/test_agent_submission.py tests/test_alpha_submit.py tests/test_agent_store.py -v`

Expected: PASS, with `runner.run.assert_not_called()` in all mismatched states.

```powershell
git add agent/reporting.py agent/nodes/submission.py agent/store.py tests/test_agent_submission.py
git commit -m "feat(agent): enforce report-bound human approval"
```

---

### Task 13: A-M Coordinator, Feedback Loops, Stop Conditions, and Resume

**Files:**
- Create: `agent/coordinator.py`
- Test: `tests/test_agent_coordinator.py`

- [ ] **Step 1: Write failing end-to-end coordinator tests**

```python
from collections import Counter, deque
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock

from wqb_cli.agent.coordinator import AgentCoordinator
from wqb_cli.agent.policy import AgentPolicy
from wqb_cli.agent.store import AgentStore
from wqb_cli.agent.types import Budget, NodeResult, RunConfig, RunState, WorkflowNode


def node_result(node: WorkflowNode, next_node: WorkflowNode | None, **payload: object) -> NodeResult:
    return NodeResult(node=node, summary={"ok": True}, next_node=next_node, payload=dict(payload))


class ScriptedNodeRunner:
    def __init__(self, script: dict[WorkflowNode, list[NodeResult]]) -> None:
        self.script = {node: deque(results) for node, results in script.items()}
        self.calls: Counter[WorkflowNode] = Counter()

    def run(self, run_id: str, node: WorkflowNode, context: dict[str, object]) -> NodeResult:
        self.calls[node] += 1
        return self.script[node].popleft()


def successful_script() -> dict[WorkflowNode, list[NodeResult]]:
    return {
        WorkflowNode.A: [node_result(WorkflowNode.A, WorkflowNode.B)],
        WorkflowNode.B: [node_result(WorkflowNode.B, WorkflowNode.C)],
        WorkflowNode.C: [node_result(WorkflowNode.C, WorkflowNode.D)],
        WorkflowNode.D: [node_result(WorkflowNode.D, WorkflowNode.F, scope={"region": "USA", "delay": 1, "universe": "TOP3000", "neutralization": "SUBINDUSTRY", "category": "PV"})],
        WorkflowNode.F: [node_result(WorkflowNode.F, WorkflowNode.G)],
        WorkflowNode.G: [node_result(WorkflowNode.G, WorkflowNode.H)],
        WorkflowNode.H: [node_result(WorkflowNode.H, WorkflowNode.I)],
        WorkflowNode.I: [node_result(WorkflowNode.I, WorkflowNode.J, new_fingerprints=["fp-1"])],
        WorkflowNode.J: [node_result(WorkflowNode.J, WorkflowNode.K)],
        WorkflowNode.K: [node_result(WorkflowNode.K, WorkflowNode.L)],
        WorkflowNode.L: [node_result(WorkflowNode.L, WorkflowNode.M, alpha_id="ALPHA1", final_report={"alpha_id": "ALPHA1"})],
    }


class AgentCoordinatorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.store = AgentStore(Path(self.temp.name) / "agent.sqlite3")
        self.store.initialize()
        self.submission = Mock()

    def tearDown(self) -> None:
        self.temp.cleanup()

    def coordinator(self, script: dict[WorkflowNode, list[NodeResult]]) -> tuple[AgentCoordinator, ScriptedNodeRunner]:
        runner = ScriptedNodeRunner(script)
        coordinator = AgentCoordinator(
            store=self.store, policy=AgentPolicy(Budget()), node_runner=runner,
            submission=self.submission,
        )
        return coordinator, runner

    @staticmethod
    def manual_scope() -> RunConfig:
        return RunConfig.from_dict({"scope_mode": "manual", "region": "USA", "delay": 1, "universe": "TOP3000", "neutralization": "SUBINDUSTRY"})

    def test_success_path_stops_at_approval(self) -> None:
        coordinator, runner = self.coordinator(successful_script())
        result = coordinator.run_manual(run_id="run-1", scope=self.manual_scope())
        self.assertEqual(result.state, RunState.AWAITING_APPROVAL)
        self.submission.submit.assert_not_called()
        self.assertEqual(runner.calls[WorkflowNode.K], 1)

    def test_k_expression_route_reenters_i_with_new_attempt(self) -> None:
        script = successful_script()
        script[WorkflowNode.I] = [node_result(WorkflowNode.I, WorkflowNode.J, new_fingerprints=["fp-1"]), node_result(WorkflowNode.I, WorkflowNode.J, new_fingerprints=["fp-2"])]
        script[WorkflowNode.J] = [node_result(WorkflowNode.J, WorkflowNode.K), node_result(WorkflowNode.J, WorkflowNode.K)]
        script[WorkflowNode.K] = [node_result(WorkflowNode.K, WorkflowNode.I), node_result(WorkflowNode.K, WorkflowNode.L)]
        coordinator, runner = self.coordinator(script)
        result = coordinator.run_manual(run_id="run-1", scope=self.manual_scope())
        self.assertEqual(runner.calls[WorkflowNode.I], 2)
        self.assertEqual(result.state, RunState.AWAITING_APPROVAL)

    def test_two_cycles_without_new_fingerprint_stop_no_progress(self) -> None:
        script = successful_script()
        script[WorkflowNode.I] = [node_result(WorkflowNode.I, WorkflowNode.J, new_fingerprints=[]), node_result(WorkflowNode.I, WorkflowNode.J, new_fingerprints=[])]
        script[WorkflowNode.J] = [node_result(WorkflowNode.J, WorkflowNode.K), node_result(WorkflowNode.J, WorkflowNode.K)]
        script[WorkflowNode.K] = [node_result(WorkflowNode.K, WorkflowNode.I), node_result(WorkflowNode.K, WorkflowNode.I)]
        coordinator, runner = self.coordinator(script)
        result = coordinator.run_manual(run_id="run-1", scope=self.manual_scope())
        self.assertEqual(result.state, RunState.NO_PROGRESS)
        self.submission.finalize_record_only.assert_called_once()
        self.submission.submit.assert_not_called()

    def test_resume_starts_after_latest_completed_node(self) -> None:
        config = self.manual_scope()
        self.store.create_run("run-1", config)
        self.store.transition("run-1", RunState.RUNNING, reason="test")
        for node in [WorkflowNode.A, WorkflowNode.B, WorkflowNode.C, WorkflowNode.D, WorkflowNode.F, WorkflowNode.G, WorkflowNode.H, WorkflowNode.I, WorkflowNode.J]:
            attempt = self.store.start_node_attempt("run-1", node)
            self.store.finish_node_attempt(attempt, "COMPLETED", {"ok": True})
        script = {WorkflowNode.K: [node_result(WorkflowNode.K, WorkflowNode.L)], WorkflowNode.L: [node_result(WorkflowNode.L, WorkflowNode.M, alpha_id="ALPHA1", final_report={"alpha_id": "ALPHA1"})]}
        coordinator, runner = self.coordinator(script)
        coordinator.resume("run-1")
        self.assertEqual(runner.calls[WorkflowNode.J], 0)
        self.assertEqual(runner.calls[WorkflowNode.K], 1)
```

- [ ] **Step 2: Run tests and verify missing coordinator**

Run: `python -m pytest tests/test_agent_coordinator.py -v`

Expected: FAIL because `agent/coordinator.py` does not exist.

- [ ] **Step 3: Implement the explicit state graph**

Use the first-version REGULAR path `A -> B -> C -> D -> F -> G -> H -> I -> J -> K`. E is intentionally absent because SUPER is out of scope. K may return F/G/H/I/L only. L returns K or M. A successful M-precondition generates the final report and transitions to AWAITING_APPROVAL without invoking submission. The production coordinator receives a `NodeRunner` protocol with the same `run(run_id, node, context) -> NodeResult` interface used by `ScriptedNodeRunner`; a small registry adapter dispatches to the A-D, F-G, H-I, J-L classes.

Represent the transition map as data, not nested model-controlled loops:

```python
FORWARD = {
    WorkflowNode.A: WorkflowNode.B, WorkflowNode.B: WorkflowNode.C,
    WorkflowNode.C: WorkflowNode.D, WorkflowNode.D: WorkflowNode.F,
    WorkflowNode.F: WorkflowNode.G, WorkflowNode.G: WorkflowNode.H,
    WorkflowNode.H: WorkflowNode.I, WorkflowNode.I: WorkflowNode.J,
    WorkflowNode.J: WorkflowNode.K,
}
K_ROUTES = {WorkflowNode.F, WorkflowNode.G, WorkflowNode.H, WorkflowNode.I, WorkflowNode.L}
```

Before every node, reload and include its `workflow/nodes/<name>/node.md` rules in the node context manifest. Start and finish one durable node attempt around every call.

- [ ] **Step 4: Implement budgets, terminal reports, and pause states**

Before I, J, and every model call, query usage from the store and apply Task 6. If a hard limit triggers, call M record-only finalization and set BUDGET_EXHAUSTED. Track fingerprints produced between K visits; two consecutive visits with no new fingerprint produce NO_PROGRESS. After every K diagnosis, store one structured experience per evaluated candidate; after M, update those records with final decision, approval outcome, and terminal artifact IDs. Authentication failures become NEEDS_AUTH. Exhausted Planner retries become PAUSED_MODEL and never fall back to Operator. Unexpected failures record node failure and set FAILED.

- [ ] **Step 5: Implement checkpoint resume**

`resume(run_id)` reads run state and latest completed attempt. NEEDS_AUTH and PAUSED_MODEL may transition back to RUNNING after their prerequisites pass. Resume from the next forward node, or from the persisted K/L route. For an incomplete J, re-enter J: Task 7's ledger converts known Simulation resources to `sim get`. For AWAITING_APPROVAL, resume only reports the pending approval; it does not submit.

- [ ] **Step 6: Verify and commit**

Run: `python -m pytest tests/test_agent_coordinator.py tests/test_agent_submission.py tests/test_agent_evaluation_nodes.py -v`

Expected: PASS.

```powershell
git add agent/coordinator.py tests/test_agent_coordinator.py
git commit -m "feat(agent): orchestrate resumable bounded research runs"
```

---

### Task 14: Agent CLI, Model Selection, Status, History, and Approval Commands

**Files:**
- Create: `commands/agent.py`
- Modify: `cli.py`
- Modify: `agent/config.py`
- Modify: `agent/reporting.py`
- Modify: `core/secrets.py`
- Test: `tests/test_agent_cli.py`
- Modify: `tests/test_cli_smoke.py`

- [ ] **Step 1: Write failing CLI parser and handler tests**

```python
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from wqb_cli.cli import build_parser


class AgentCliTests(unittest.TestCase):
    def test_manual_run_parser_requires_scope_values_in_handler_validation(self) -> None:
        args = build_parser().parse_args(["agent", "run", "--scope-mode", "manual", "--region", "USA"])
        self.assertEqual(args.agent_command, "run")
        self.assertEqual(args.scope_mode, "manual")

    def test_model_role_and_per_run_overrides_parse(self) -> None:
        args = build_parser().parse_args(["agent", "run", "--scope-mode", "auto", "--planner-model", "large", "--operator-model", "small"])
        self.assertEqual(args.planner_model, "large"); self.assertEqual(args.operator_model, "small")

    @patch("wqb_cli.commands.agent.build_service")
    def test_approve_delegates_only_to_approval_service(self, build_service) -> None:
        service = build_service.return_value; service.approve.return_value = {"ok": True, "state": "SUBMITTED"}
        from wqb_cli.commands.agent import handle_agent
        args = build_parser().parse_args(["agent", "approve", "run-1"])
        self.assertEqual(handle_agent(args), 0); service.approve.assert_called_once_with("run-1")

    @patch("wqb_cli.commands.agent.getpass.getpass", return_value="secret-value")
    @patch("wqb_cli.commands.agent.set_named_secret")
    def test_model_set_key_reads_secret_without_cli_argument(self, set_secret, getpass) -> None:
        from wqb_cli.commands.agent import handle_agent
        args = build_parser().parse_args(["agent", "models", "set-key", "planner"])
        handle_agent(args)
        set_secret.assert_called_once(); self.assertNotIn("secret-value", repr(args))
```

- [ ] **Step 2: Run tests and verify the missing command registration**

Run: `python -m pytest tests/test_agent_cli.py -v`

Expected: FAIL because `commands/agent.py` and the `agent` parser are absent.

- [ ] **Step 3: Add the complete argparse command tree**

`add_agent_parser` creates group-level `--config`, `--database`, and `--run-root` options, then these subcommands:

```text
run --scope-mode {manual,auto} [--region --delay --universe --neutralization]
    [--planner-model --operator-model] [--max-rounds --max-simulations
     --max-runtime-minutes --max-planner-calls --max-operator-calls
     --max-model-cost-usd]
resume RUN_ID
status RUN_ID
approve RUN_ID
reject RUN_ID --reason TEXT
history [--limit N --state STATE]
models list
models set ROLE --provider PROVIDER --api-style STYLE --model MODEL
    [--base-url URL] [--reasoning LEVEL] [--secret-name NAME]
    [--structured-outputs {true,false}] [--fallback-model MODEL]
    [--input-cost-per-million USD] [--output-cost-per-million USD]
models set-key ROLE
models test [ROLE]
eval [--suite SUITE] [--live] [--max-simulations 1]
```

`models set-key` reads through `getpass.getpass`; there is no API-key argument and no printed key. Add `set_named_secret(secret_name, value, service="wqb-cli")` to `core/secrets.py`.

- [ ] **Step 4: Implement handlers and service construction**

`build_service(args)` loads AgentConfig, applies path/model/budget overrides, initializes the store, adapters, router, writer, runner, nodes, coordinator, reporting, and submission service. Status/history/model list do not require model keys. Run and model test fail with structured JSON naming the missing role configuration or secret reference.

Add `status_projection(store, run_id)` and `history_projection(store, limit, state)` to `agent/reporting.py`. Status returns run state, latest node/attempt, locked scope, plan version/hash, budgets consumed/remaining, per-role calls/tokens/cost/latency/failures, last error, and permitted next action. History returns the same stable summary fields without raw prompts or secrets. `models list` masks key material and reports only provider, API style, model ID, endpoint host, secret reference name, and whether that keyring entry exists. `models test` sends one schema-validated self-test request through the selected role and records it as `purpose=model_healthcheck`, not as research experience.

`handle_agent` writes one JSON result and returns exit code 0 for CREATED/RUNNING/AWAITING_APPROVAL/SUBMITTED/REJECTED and bounded terminal research outcomes, 1 for FAILED/configuration errors, and 2 for invalid user input. `approve` obtains the exact stored final report/Alpha subject, records the human approval, and invokes Task 12. `reject` never invokes Runner.

- [ ] **Step 5: Register dispatch and add subprocess smoke coverage**

Import `add_agent_parser`/`handle_agent` in `cli.py`, register the parser in `build_parser`, and dispatch before the unknown-command branch. Extend `tests/test_cli_smoke.py`:

```python
def test_agent_help_exposes_safe_workflow_commands(self) -> None:
    result = run_wqb("agent", "--help")
    self.assertEqual(result.returncode, 0, result.stderr)
    for name in ["run", "resume", "status", "approve", "reject", "history", "models", "eval"]:
        self.assertIn(name, result.stdout)

def test_agent_models_set_key_has_no_secret_argument(self) -> None:
    result = run_wqb("agent", "models", "set-key", "--help")
    self.assertEqual(result.returncode, 0, result.stderr)
    self.assertNotIn("--api-key", result.stdout)
```

- [ ] **Step 6: Verify and commit**

Run: `python -m pytest tests/test_agent_cli.py tests/test_cli_smoke.py -v`

Expected: PASS.

```powershell
git add commands/agent.py cli.py agent/config.py agent/reporting.py core/secrets.py tests/test_agent_cli.py tests/test_cli_smoke.py
git commit -m "feat(agent): expose research and model selection commands"
```

---

### Task 15: Offline Evaluation, Role Metrics, and Security Regression Suite

**Files:**
- Create: `agent/eval.py`
- Create: `tests/test_agent_eval.py`
- Modify: `commands/agent.py`

- [ ] **Step 1: Write failing evaluation metric tests**

```python
import unittest

from wqb_cli.agent.eval import EvaluationCase, EvaluationRunner


def case(name: str, **overrides: object) -> EvaluationCase:
    observation = {
        "terminal_state": "AWAITING_APPROVAL", "expected_terminal_state": "AWAITING_APPROVAL",
        "routes": [], "expected_routes": [], "candidate_count": 1, "valid_candidate_count": 1,
        "decision_count": 1, "cited_decision_count": 1, "invalid_citation_count": 0,
        "duplicate_count": 0, "blocked_duplicate_count": 0, "resume_replayed_side_effects": 0,
        "simulation_count": 1, "simulation_budget": 1, "approval_gate_violations": 0,
        "model_roles": ["planner"], "expected_model_roles": ["planner"],
        "blocked_operator_privilege_violations": 0, "network_used": False,
        "command_prefixes": [("sim", "create")], "planner_calls": 1, "operator_calls": 0,
        "planner_tokens": 20, "operator_tokens": 0, "planner_latency_ms": 5,
        "operator_latency_ms": 0, "planner_failures": 0, "operator_failures": 0,
    }
    observation.update(overrides)
    return EvaluationCase(name=name, execute=lambda: dict(observation))


class AgentEvalTests(unittest.TestCase):
    def test_offline_suite_reports_role_and_safety_metrics(self) -> None:
        passing = case("pass")
        routed = case("route", routes=["I"], expected_routes=["I"])
        escalation = case("operator-escalation", blocked_operator_privilege_violations=1, model_roles=["operator"], expected_model_roles=["operator"])
        runner = EvaluationRunner(cases=[passing, routed, escalation])
        result = runner.run(live=False)
        self.assertEqual(result["case_count"], 3)
        self.assertEqual(result["approval_gate_violations"], 0)
        self.assertEqual(result["budget_violations"], 0)
        self.assertEqual(result["role_routing_accuracy"], 1.0)
        self.assertEqual(result["diagnosis_route_accuracy"], 1.0)
        self.assertEqual(result["blocked_operator_privilege_violations"], 1)

    def test_offline_suite_never_uses_network_or_submit(self) -> None:
        passing = case("pass")
        result = EvaluationRunner(cases=[passing]).run(live=False)
        observation = passing.execute()
        self.assertFalse(observation["network_used"])
        self.assertNotIn(("alpha", "submit"), observation["command_prefixes"])
        self.assertEqual(result["approval_gate_violations"], 0)
```

- [ ] **Step 2: Run tests and verify missing evaluation runner**

Run: `python -m pytest tests/test_agent_eval.py -v`

Expected: FAIL because `agent/eval.py` does not exist.

- [ ] **Step 3: Implement fixed offline cases and metric aggregation**

`EvaluationCase` contains `name` and an `execute: Callable[[], dict[str, object]]`. Production cases use this callable to run the Coordinator with deterministic fake model and command transcripts in isolated temporary stores/run roots; the simple observations above test aggregation itself. Each observation contains expected/actual terminal state, expected/actual K routes, valid/invalid candidates, citation counts, expected/actual model roles, side-effect replay counts, simulation budget/usage, command prefixes, network usage, and per-role usage. `EvaluationRunner.run(live=False)` returns:

```python
METRIC_KEYS = (
    "candidate_validity_rate", "citation_coverage", "invalid_citation_count",
    "diagnosis_route_accuracy", "duplicate_avoidance_rate", "resume_idempotency",
    "pass_at_budget", "budget_violations", "approval_gate_violations",
    "role_routing_accuracy", "blocked_operator_privilege_violations",
    "planner_calls", "operator_calls", "planner_tokens", "operator_tokens",
    "planner_latency_ms", "operator_latency_ms", "planner_failures", "operator_failures",
)
```

Avoid division-by-zero by returning `None` for a rate with no eligible denominator. Count privilege violations as successful blocks, not leaks. Return `ok=False` if budget or approval violations are nonzero, or a scenario's expected terminal/route differs.

- [ ] **Step 4: Add the explicit live-test boundary**

`--live` requires both `WQB_AGENT_LIVE_TEST=1` and `--max-simulations 1`; otherwise return a structured refusal. Build a Runner policy for live evaluation that removes `("alpha", "submit")` from every node including M and forces record-only finalization. Live output is stored under a run marked `evaluation=true` and never imported as successful experience.

- [ ] **Step 5: Wire `wqb agent eval` and verify**

Run: `python -m pytest tests/test_agent_eval.py tests/test_agent_coordinator.py -v`

Expected: PASS.

Run: `python -m wqb_cli agent eval`

Expected: JSON with `ok: true`, zero budget/approval violations, and no network access.

```powershell
git add agent/eval.py commands/agent.py tests/test_agent_eval.py
git commit -m "test(agent): add offline workflow evaluation"
```

---

### Task 16: Thin Agent Skill, Documentation, Packaging, and Full Verification

**Files:**
- Create: `skills/wqb-quant-agent/SKILL.md`
- Modify: `README.md`
- Modify: `README_CN.md`
- Modify: `pyproject.toml`
- Modify: `__init__.py`
- Modify: `MANIFEST.in`
- Modify: `CHANGELOG.md`
- Test: `tests/test_agent_cli.py`

> Before editing the Skill, invoke `skill-creator` and `superpowers:writing-skills` and follow their current instructions.

- [ ] **Step 1: Add a failing packaged-Skill test**

```python
def test_quant_agent_skill_is_present_and_forbids_direct_submit(self) -> None:
    skill = Path(__file__).resolve().parents[1] / "skills" / "wqb-quant-agent" / "SKILL.md"
    self.assertTrue(skill.exists())
    text = skill.read_text(encoding="utf-8")
    self.assertIn("wqb agent approve", text)
    self.assertIn("Never call `wqb alpha submit` directly", text)
    self.assertIn("planner", text.lower()); self.assertIn("operator", text.lower())
```

Run: `python -m pytest tests/test_agent_cli.py::AgentCliTests::test_quant_agent_skill_is_present_and_forbids_direct_submit -v`

Expected: FAIL because the Skill does not exist.

- [ ] **Step 2: Create the thin Skill**

Use this functional content, expanding only with setup/status examples required by the invoked skill-authoring instructions:

```markdown
---
name: wqb-quant-agent
description: Run, resume, inspect, approve, or reject the repository's bounded multi-model WorldQuant BRAIN research agent.
---

# WQB Quant Agent

Use `wqb agent` as the only orchestration entry point.

1. Inspect `wqb agent models list` and configure missing Planner/Operator roles.
2. Start manual scope with explicit region, delay, universe, and neutralization, or use explicit auto scope.
3. Use `wqb agent status RUN_ID` and `wqb agent resume RUN_ID`; do not reproduce A-M logic in the conversation.
4. Present the final report and exact Alpha ID when state is `AWAITING_APPROVAL`.
5. Call `wqb agent approve RUN_ID` only after the user explicitly approves that report. Use `reject` when declined.

Never call `wqb alpha submit` directly. Never expose API keys, cookies, or `.env` content. Never bypass budgets, model roles, or the approval hash.
```

- [ ] **Step 3: Document setup and operating workflow in both READMEs**

Document model setup, keyring commands, manual/auto runs, status/resume, budget semantics, Planner/Operator responsibilities, report-bound approval, offline eval, and the fact that `run` performs real simulations. Include no real key, model entitlement claim, or hard-coded provider model default.

Reference the current official OpenAI Structured Outputs guide for the Responses adapter: `https://developers.openai.com/api/docs/guides/structured-outputs`. Explain that compatible endpoints must support the configured API style and may use local schema repair when strict Structured Outputs are unavailable.

- [ ] **Step 4: Package files and align versions**

Set `pyproject.toml` project version and `__init__.__version__` to `0.4.0`. Confirm `[tool.setuptools].packages` contains `wqb_cli`, `wqb_cli.commands`, `wqb_cli.core`, `wqb_cli.agent`, `wqb_cli.agent.models`, and `wqb_cli.agent.nodes`. Add `skills/**/*.md` to `tool.setuptools.package-data.wqb_cli` and `recursive-include skills *.md` to `MANIFEST.in`. Add a 0.4.0 entry in `CHANGELOG.md` listing multi-model routing, bounded runs, recovery, structured experience, approval, and eval.

- [ ] **Step 5: Run focused documentation/package tests**

Run: `python -m pytest tests/test_agent_cli.py tests/test_cli_smoke.py -v`

Expected: PASS.

Run: `python -m build`

Expected: PASS and both sdist/wheel contain `skills/wqb-quant-agent/SKILL.md` and `jsonschema` metadata. Inspect with:

```powershell
tar -tf (Get-ChildItem dist\wqb_cli-0.4.0.tar.gz).FullName | Select-String "wqb-quant-agent/SKILL.md"
```

- [ ] **Step 6: Run the complete verification suite**

Run: `python -m pytest tests -v`

Expected: all tests PASS with no network access.

Run: `python -m wqb_cli agent eval`

Expected: `ok` is true; `budget_violations` and `approval_gate_violations` are 0.

Run: `python -m wqb_cli agent --help`

Expected: lists `run`, `resume`, `status`, `approve`, `reject`, `history`, `models`, and `eval`.

Run: `git status --short`

Expected: only intended source, test, documentation, and plan-tracking changes are present; `local/`, `research_runs/`, `dist/`, and build artifacts remain ignored.

- [ ] **Step 7: Commit the release-ready implementation**

```powershell
git add skills README.md README_CN.md pyproject.toml __init__.py MANIFEST.in CHANGELOG.md tests/test_agent_cli.py
git commit -m "docs(agent): ship quant agent workflow and skill"
```

---

## Spec Coverage Matrix

| Design requirement | Implementation tasks |
| --- | --- |
| Manual and automatic REGULAR FASTEXPR scope | 1, 9, 13, 14 |
| Deterministic A-M graph and bounded F/G/H/I routes | 6, 9-13 |
| Planner/Operator separation and configurable providers | 4-6, 10-11, 14 |
| Optional Operator same-role fallback and separate costs | 1, 3, 5-6, 14-15 |
| Semantic context, evidence references, and secret redaction | 4, 6-7, 10 |
| Restricted real `wqb` execution and Simulation recovery | 3, 6-7, 11, 13 |
| FASTEXPR validation and deduplication | 8, 10-11 |
| SQLite run state and structured experience | 2-3, 10, 13-14 |
| Report-bound human approval and no pre-approval submit | 6-7, 12-14 |
| Offline eval, role metrics, and optional non-submit live smoke | 15 |
| Thin Skill, bilingual docs, and distributable package | 16 |

---

## Execution Checkpoints

After Task 3: SQLite can create/resume runs and enforce idempotent records without models or network.

After Task 6: Planner/Operator calls are schema-validated, role-routed, budgeted, and context-isolated.

After Task 10: A-D and F-I can produce a validated candidate batch with fake platform/model inputs.

After Task 13: The complete fake A-M loop reaches bounded terminal states and never submits before approval.

After Task 16: CLI, eval, Skill, docs, package artifacts, and the full offline suite are release-ready.
