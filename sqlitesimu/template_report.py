from __future__ import annotations

import csv
import hashlib
import io
import json
import math
import re
import statistics
from collections import Counter, defaultdict
from dataclasses import dataclass
from typing import Any

from .models import RUN_TERMINAL_STATES, CandidateSpec, SimulationManifest


TEMPLATE_FORMAT_VERSION = 1
TEMPLATE_REPORT_FORMAT_VERSION = 1

_NAME_PATTERN = re.compile(r"# \[([A-Za-z][A-Za-z0-9 .&+:/_-]*)\]")
_VERSION_PATTERN = re.compile(
    r"# \[(\d{8})\] - \[([^\]\r\n]+)\] - \[epoch ([1-9]\d*)\]",
    re.IGNORECASE,
)
_ASSIGNMENT_PATTERN = re.compile(r"([A-Za-z_][A-Za-z0-9_]*)\s*=")
_PLACEHOLDER_PATTERN = re.compile(r"\{[A-Za-z][A-Za-z0-9_]*\}")
_REQUIRED_LINEAGE = (
    "workflow_run_id",
    "template_family_id",
    "template_version",
    "template_name",
    "template_name_zh",
    "template_logic_zh",
    "template_epoch",
    "family_ordinal",
    "family_draw_index",
    "mechanism_id",
    "field_roles",
    "parameters",
    "rng_seed",
    "population_ordinal",
    "expression_hash",
    "calculation_hash",
    "settings_hash",
    "single_mechanism",
)
_METRICS = (
    ("sharpe", "sharpe"),
    ("fitness", "fitness"),
    ("turnover", "turnover"),
    ("margin", "margin"),
    ("returns", "returns_value"),
    ("drawdown", "drawdown"),
    ("pnl", "pnl"),
)
_CHECK_STATUSES = ("FAIL", "PASS", "PENDING", "WARNING", "ERROR")


@dataclass(frozen=True)
class TemplateHeader:
    name: str
    date: str
    version_label: str
    epoch: int


def parse_template_header(expression: str) -> TemplateHeader | None:
    lines = expression.strip().splitlines()
    if len(lines) < 2:
        return None
    name = _NAME_PATTERN.fullmatch(lines[0].strip())
    version = _VERSION_PATTERN.fullmatch(lines[1].strip())
    if not name or not version:
        return None
    return TemplateHeader(
        name=name.group(1),
        date=version.group(1),
        version_label=version.group(2),
        epoch=int(version.group(3)),
    )


def expression_hash(expression: str) -> str:
    normalized = expression.replace("\r\n", "\n").replace("\r", "\n").strip()
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def calculation_hash(expression: str) -> str:
    lines = expression.replace("\r\n", "\n").replace("\r", "\n").strip().splitlines()
    normalized = "\n".join(
        line.rstrip()
        for line in lines[2:]
        if line.strip() and not line.lstrip().startswith("#")
    )
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def settings_hash(settings: dict[str, Any]) -> str:
    encoded = json.dumps(
        settings,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def validate_template_manifest(manifest: SimulationManifest) -> dict[str, Any]:
    errors: list[dict[str, Any]] = []
    identities: dict[tuple[str, str], TemplateHeader] = {}
    family_counts: Counter[str] = Counter()
    first_settings_hash: tuple[str, int] | None = None
    first_workflow_run_id: tuple[str, int] | None = None
    calculation_identities: dict[tuple[str, str], int] = {}

    for index, candidate in enumerate(manifest.candidates):
        candidate_errors = _validate_template_candidate(candidate, index=index)
        errors.extend(candidate_errors)
        metadata = candidate.metadata
        family_id = str(metadata.get("template_family_id") or "")
        family_counts[family_id or "UNASSIGNED"] += 1
        expression = candidate.payload.get("regular")
        header = parse_template_header(expression) if isinstance(expression, str) else None
        settings = candidate.payload["settings"]
        actual_settings_hash = settings_hash(settings)
        workflow_run_id = str(metadata.get("workflow_run_id") or "")
        if first_settings_hash is None:
            first_settings_hash = (actual_settings_hash, index)
        elif actual_settings_hash != first_settings_hash[0]:
            errors.append(
                _issue(
                    index,
                    "settings_drift",
                    f"Settings differ from candidate {first_settings_hash[1]}",
                )
            )
        if workflow_run_id:
            if first_workflow_run_id is None:
                first_workflow_run_id = (workflow_run_id, index)
            elif workflow_run_id != first_workflow_run_id[0]:
                errors.append(
                    _issue(
                        index,
                        "workflow_run_id_mismatch",
                        f"workflow_run_id differs from candidate {first_workflow_run_id[1]}",
                    )
                )
        if isinstance(expression, str):
            calculation_identity = (calculation_hash(expression), actual_settings_hash)
            previous_index = calculation_identities.get(calculation_identity)
            if previous_index is not None:
                errors.append(
                    _issue(
                        index,
                        "duplicate_calculation_identity",
                        f"Executable calculation duplicates candidate {previous_index}",
                    )
                )
            else:
                calculation_identities[calculation_identity] = index
        if not family_id or header is None:
            continue
        key = (family_id, str(metadata.get("template_version") or ""))
        previous = identities.get(key)
        if previous is not None and previous != header:
            errors.append(
                _issue(
                    index,
                    "inconsistent_template_header",
                    f"{family_id} has more than one header for template_version",
                )
            )
        else:
            identities[key] = header

    verdict = not errors
    return {
        "ok": verdict,
        "verdict": verdict,
        "template_format_version": TEMPLATE_FORMAT_VERSION,
        "candidate_count": len(manifest.candidates),
        "template_count": len(family_counts),
        "family_counts": dict(sorted(family_counts.items())),
        "workflow_run_id": first_workflow_run_id[0] if first_workflow_run_id else None,
        "settings_hash": first_settings_hash[0] if first_settings_hash else None,
        "violation_count": len(errors),
        "violations": errors,
    }


def build_template_report(export_payload: dict[str, Any]) -> dict[str, Any]:
    run = export_payload.get("run")
    experiments = export_payload.get("experiments")
    results = export_payload.get("results")
    checks = export_payload.get("checks", [])
    if not isinstance(run, dict):
        raise ValueError("Export must contain a run object")
    if run.get("state") not in RUN_TERMINAL_STATES:
        raise ValueError("Template reports require a terminal run export")
    if not isinstance(experiments, list) or not isinstance(results, list):
        raise ValueError("Export must contain experiments and results arrays")
    if not isinstance(checks, list):
        raise ValueError("Export checks must be an array")

    identities: dict[str, dict[str, Any]] = {}
    family_experiments: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for experiment in experiments:
        if not isinstance(experiment, dict):
            continue
        identity = _template_identity(experiment)
        experiment_id = str(experiment.get("experiment_id") or "")
        identities[experiment_id] = identity
        family_experiments[identity["key"]].append(experiment)

    result_rows: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for result in results:
        if not isinstance(result, dict):
            continue
        experiment_id = str(result.get("experiment_id") or "")
        identity = identities.get(experiment_id) or _template_identity(result)
        identities.setdefault(experiment_id, identity)
        result_rows[identity["key"]].append(result)

    checks_by_alpha: dict[str, list[dict[str, Any]]] = defaultdict(list)
    checks_by_family: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for check in checks:
        if not isinstance(check, dict):
            continue
        alpha_id = str(check.get("alpha_id") or "")
        experiment_id = str(check.get("experiment_id") or "")
        identity = identities.get(experiment_id) or _template_identity(check)
        checks_by_alpha[alpha_id].append(check)
        checks_by_family[identity["key"]].append(check)

    family_keys = sorted(
        set(family_experiments) | set(result_rows),
        key=lambda key: _family_sort_key(
            family_experiments.get(key, []),
            result_rows.get(key, []),
            key,
        ),
    )
    family_identity = {
        key: _family_identity(key, family_experiments.get(key, []), result_rows.get(key, []))
        for key in family_keys
    }

    performance = []
    check_statistics = []
    representatives = []
    state_counts: Counter[str] = Counter()
    for key in family_keys:
        assigned = family_experiments.get(key, [])
        ready = result_rows.get(key, [])
        identity = family_identity[key]
        counts = Counter(_simulation_state(row.get("state")) for row in assigned)
        state_counts.update(counts)
        performance.append(
            {
                **identity,
                "assigned_count": len(assigned),
                "ready_count": len(ready),
                "no_trade_count": sum(_is_no_trade(row) for row in ready),
                "state_counts": dict(sorted(counts.items())),
                "metrics": {
                    display_name: _describe(
                        [_finite_float(row.get(source_name)) for row in ready]
                    )
                    for display_name, source_name in _METRICS
                },
            }
        )
        check_statistics.extend(
            _check_statistics(identity, checks_by_family.get(key, []))
        )
        representatives.extend(
            _representatives(identity, ready, checks_by_alpha)
        )

    reasons = _ineligibility_reasons(
        run,
        state_counts,
        family_identity.values(),
        assigned_count=len(experiments),
        result_count=len(results),
    )
    assessments = _family_assessments(
        performance,
        check_statistics,
        representatives,
        expansion_screen_eligible=not reasons,
    )
    return {
        "ok": True,
        "template_report_format_version": TEMPLATE_REPORT_FORMAT_VERSION,
        "source": {
            "run_id": run.get("run_id"),
            "run_state": run.get("state"),
            "database": export_payload.get("database"),
            "schema_version": export_payload.get("schema_version"),
        },
        "summary": {
            "assigned_count": len(experiments),
            "ready_count": len(results),
            "template_count": len(family_keys),
            "state_counts": dict(sorted(state_counts.items())),
            "checks_available": "checks" in export_payload,
            "analysis_eligible": not reasons,
            "ineligibility_reasons": reasons,
        },
        "sections": {
            "template_alphas_performance_each_template": performance,
            "template_alphas_checks_statistics": check_statistics,
            "template_alphas_best_performance_each_metric": representatives,
        },
        "template_assessments": assessments,
    }


def render_template_report_markdown(report: dict[str, Any]) -> str:
    sections = report["sections"]
    lines = [
        "# Template Analysis Report",
        "",
        "```template alphas performance each template",
        _performance_csv(sections["template_alphas_performance_each_template"]).rstrip(),
        "```",
        "",
        "```template alphas checks statistics",
        _checks_csv(sections["template_alphas_checks_statistics"]).rstrip(),
        "```",
        "",
        "```template alphas best performance each metric",
        _representatives_csv(
            sections["template_alphas_best_performance_each_metric"]
        ).rstrip(),
        "```",
        "",
        "## Template Assessments",
        "",
    ]
    for index, assessment in enumerate(report.get("template_assessments", []), start=1):
        lines.extend(
            [
                (
                    f"### {index}. [{assessment['template_name']}]"
                    f" - {assessment['template_name_zh']}"
                ),
                "",
                f"逻辑: {assessment['template_logic_zh']}",
                "",
                f"实验成果评估: {assessment['evaluation']}",
                "",
                f"关键发现: {assessment['finding']}",
                "",
                f"改进方向: {assessment['improvement']}",
                "",
            ]
        )
    return "\n".join(lines)


def _validate_template_candidate(candidate: CandidateSpec, *, index: int) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    if candidate.payload.get("type") != "REGULAR":
        return [_issue(index, "regular_required", "Template candidates must be REGULAR")]
    expression = candidate.payload.get("regular")
    if not isinstance(expression, str):
        return [_issue(index, "expression_required", "Template expression must be text")]
    header = parse_template_header(expression)
    if header is None:
        issues.append(
            _issue(
                index,
                "invalid_template_header",
                "Expected '# [English Name]' and '# [YYYYMMDD] - [version] - [epoch N]'",
            )
        )
    metadata = candidate.metadata
    for key in _REQUIRED_LINEAGE:
        if key not in metadata or _blank(metadata[key]):
            issues.append(_issue(index, "missing_lineage", f"Missing metadata.{key}"))
    if metadata.get("single_mechanism") is not True:
        issues.append(
            _issue(index, "mixed_mechanism", "metadata.single_mechanism must be true")
        )
    if metadata.get("template_format_version") != TEMPLATE_FORMAT_VERSION:
        issues.append(
            _issue(
                index,
                "template_format_version",
                f"metadata.template_format_version must equal {TEMPLATE_FORMAT_VERSION}",
            )
        )
    if header is not None:
        expected_name = metadata.get("template_name")
        if expected_name and str(expected_name) != header.name:
            issues.append(_issue(index, "template_name_mismatch", "Header and metadata disagree"))
        expected_epoch = metadata.get("template_epoch")
        if expected_epoch not in {None, ""}:
            try:
                epoch_matches = int(expected_epoch) == header.epoch
            except (TypeError, ValueError):
                epoch_matches = False
            if not epoch_matches:
                issues.append(
                    _issue(index, "template_epoch_mismatch", "Header and metadata disagree")
                )

    for key in ("template_version", "template_epoch", "family_ordinal", "family_draw_index"):
        if key in metadata and not _positive_integer(metadata[key]):
            issues.append(
                _issue(index, "invalid_lineage_value", f"metadata.{key} must be a positive integer")
            )
    if not isinstance(metadata.get("field_roles"), dict):
        issues.append(_issue(index, "field_roles_type", "metadata.field_roles must be an object"))
    if not isinstance(metadata.get("parameters"), dict):
        issues.append(_issue(index, "parameters_type", "metadata.parameters must be an object"))
    unresolved = sorted(set(_PLACEHOLDER_PATTERN.findall(expression)))
    if unresolved:
        issues.append(
            _issue(
                index,
                "unresolved_placeholder",
                f"Candidate expression still contains placeholders: {', '.join(unresolved)}",
            )
        )

    executable = [
        line.strip()
        for line in expression.strip().splitlines()[2:]
        if line.strip() and not line.lstrip().startswith("#")
    ]
    if not executable or executable[-1] != "template_LLM":
        issues.append(
            _issue(index, "final_variable", "The final executable line must be template_LLM")
        )
    assignments: list[str] = []
    for line in executable[:-1]:
        if not line.endswith(";"):
            issues.append(
                _issue(index, "statement_terminator", f"Assignment must end with ';': {line}")
            )
        assignment = _ASSIGNMENT_PATTERN.match(line)
        if assignment is None:
            issues.append(
                _issue(index, "assignment_required", f"Expected a named variable assignment: {line}")
            )
        else:
            assignments.append(assignment.group(1))
    duplicates = sorted(name for name, count in Counter(assignments).items() if count > 1)
    if duplicates:
        issues.append(
            _issue(
                index,
                "duplicate_variable",
                f"Variables may be assigned once: {', '.join(duplicates)}",
            )
        )
    invalid_names = sorted(
        name for name in assignments if name != "template_LLM" and not name.endswith("_variable")
    )
    if invalid_names:
        issues.append(
            _issue(
                index,
                "variable_name",
                f"Intermediate variables must end with _variable: {', '.join(invalid_names)}",
            )
        )
    if assignments.count("template_LLM") != 1:
        issues.append(
            _issue(index, "template_assignment", "template_LLM must be assigned exactly once")
        )
    elif not assignments or assignments[-1] != "template_LLM":
        issues.append(
            _issue(index, "template_assignment_order", "template_LLM must be the last assignment")
        )

    recorded_expression_hash = metadata.get("expression_hash")
    if recorded_expression_hash and recorded_expression_hash != expression_hash(expression):
        issues.append(_issue(index, "expression_hash_mismatch", "Expression hash is stale"))
    recorded_calculation_hash = metadata.get("calculation_hash")
    if recorded_calculation_hash and recorded_calculation_hash != calculation_hash(expression):
        issues.append(_issue(index, "calculation_hash_mismatch", "Calculation hash is stale"))
    recorded_settings_hash = metadata.get("settings_hash")
    if recorded_settings_hash and recorded_settings_hash != settings_hash(candidate.payload["settings"]):
        issues.append(_issue(index, "settings_hash_mismatch", "Settings hash is stale"))
    return issues


def _issue(index: int, code: str, detail: str) -> dict[str, Any]:
    return {"candidate_index": index, "code": code, "detail": detail}


def _blank(value: Any) -> bool:
    if value is None or value == "":
        return True
    return isinstance(value, (dict, list, tuple, set)) and not value


def _positive_integer(value: Any) -> bool:
    if isinstance(value, bool):
        return False
    try:
        return int(value) == value and int(value) > 0
    except (TypeError, ValueError):
        return False


def _template_identity(row: dict[str, Any]) -> dict[str, Any]:
    metadata = row.get("metadata") if isinstance(row.get("metadata"), dict) else {}
    payload = row.get("payload") if isinstance(row.get("payload"), dict) else {}
    expression = row.get("regular_code") or payload.get("regular")
    header = parse_template_header(expression) if isinstance(expression, str) else None
    family_id = str(metadata.get("template_family_id") or "")
    name = str(
        metadata.get("template_name")
        or (header.name if header else "")
        or family_id
        or "UNASSIGNED"
    )
    name_zh = str(metadata.get("template_name_zh") or name)
    logic_zh = str(metadata.get("template_logic_zh") or "未记录")
    version = metadata.get("template_version")
    epoch = metadata.get("template_epoch") or (header.epoch if header else None)
    key = family_id or name
    if version not in {None, ""}:
        key = f"{key}@v{version}"
    if epoch not in {None, ""}:
        key = f"{key}@e{epoch}"
    return {
        "key": key,
        "template": f"# [{name}]",
        "template_name": name,
        "template_name_zh": name_zh,
        "template_logic_zh": logic_zh,
        "template_family_id": family_id or None,
        "template_version": version,
        "template_epoch": epoch,
    }


def _family_sort_key(
    experiments: list[dict[str, Any]],
    results: list[dict[str, Any]],
    fallback: str,
) -> tuple[int, str]:
    for row in experiments + results:
        metadata = row.get("metadata") if isinstance(row.get("metadata"), dict) else {}
        value = metadata.get("family_ordinal")
        try:
            return int(value), fallback
        except (TypeError, ValueError):
            continue
    return 10**9, fallback


def _family_identity(
    key: str,
    experiments: list[dict[str, Any]],
    results: list[dict[str, Any]],
) -> dict[str, Any]:
    rows = experiments + results
    return _template_identity(rows[0]) if rows else {
        "key": key,
        "template": "# [UNASSIGNED]",
        "template_name": "UNASSIGNED",
        "template_name_zh": "未分配",
        "template_logic_zh": "未记录",
        "template_family_id": None,
        "template_version": None,
        "template_epoch": None,
    }


def _describe(values: list[float | None]) -> dict[str, Any]:
    numeric = sorted(value for value in values if value is not None)
    if not numeric:
        return {
            "count": 0,
            "mean": None,
            "std": None,
            "min": None,
            "25%": None,
            "50%": None,
            "75%": None,
            "max": None,
        }
    return {
        "count": len(numeric),
        "mean": statistics.fmean(numeric),
        "std": statistics.stdev(numeric) if len(numeric) > 1 else None,
        "min": numeric[0],
        "25%": _percentile(numeric, 0.25),
        "50%": _percentile(numeric, 0.5),
        "75%": _percentile(numeric, 0.75),
        "max": numeric[-1],
    }


def _percentile(values: list[float], fraction: float) -> float:
    position = (len(values) - 1) * fraction
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return values[lower]
    return values[lower] + (values[upper] - values[lower]) * (position - lower)


def _is_no_trade(row: dict[str, Any]) -> bool:
    return (
        _finite_float(row.get("turnover")) == 0
        and _finite_float(row.get("long_count")) == 0
        and _finite_float(row.get("short_count")) == 0
    )


def _simulation_state(value: Any) -> str:
    state = str(value or "UNKNOWN")
    # Old exported JSON may predate schema v3; never expose its simulation-as-submit terms.
    return {
        "SUBMITTING": "SIMULATING",
        "SUBMIT_UNKNOWN": "SIMULATE_UNKNOWN",
    }.get(state, state)


def _check_statistics(
    identity: dict[str, Any],
    checks: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for check in checks:
        grouped[str(check.get("name") or "UNKNOWN")].append(check)
    output = []
    for name in sorted(grouped):
        rows = grouped[name]
        status_counts = Counter(str(row.get("result") or "UNKNOWN").upper() for row in rows)
        values = [_finite_float(row.get("value")) for row in rows]
        limits = []
        for row in rows:
            limit = row.get("limit")
            if limit is not None and limit not in limits:
                limits.append(limit)
        output.append(
            {
                **identity,
                "name": name,
                "status_counts": {
                    status: status_counts.get(status, 0) for status in _CHECK_STATUSES
                },
                "other_status_counts": {
                    status: count
                    for status, count in sorted(status_counts.items())
                    if status not in _CHECK_STATUSES
                },
                "value": _describe(values),
                "limitValues": limits,
            }
        )
    return output


def _representatives(
    identity: dict[str, Any],
    rows: list[dict[str, Any]],
    checks_by_alpha: dict[str, list[dict[str, Any]]],
) -> list[dict[str, Any]]:
    output = []
    for metric in ("sharpe", "fitness"):
        candidates = [row for row in rows if _finite_float(row.get(metric)) is not None]
        if not candidates:
            continue
        clean = [
            row
            for row in candidates
            if not any(
                str(check.get("result") or "").upper() in {"FAIL", "ERROR"}
                for check in checks_by_alpha.get(str(row.get("alpha_id") or ""), [])
            )
        ]
        pool = clean or candidates
        selected = max(
            pool,
            key=lambda row: (
                _finite_float(row.get(metric)),
                str(row.get("alpha_id") or ""),
            ),
        )
        alpha_id = str(selected.get("alpha_id") or "")
        output.append(
            {
                **identity,
                "metric": metric,
                "selection_scope": "no_fail_or_error" if clean else "all_ready_fallback",
                "alpha_id": alpha_id or None,
                "experiment_id": selected.get("experiment_id"),
                "regular_code": selected.get("regular_code"),
                "sharpe": selected.get("sharpe"),
                "fitness": selected.get("fitness"),
                "turnover": selected.get("turnover"),
                "margin": selected.get("margin"),
                "returns": selected.get("returns_value"),
                "drawdown": selected.get("drawdown"),
                "pnl": selected.get("pnl"),
                "metadata": selected.get("metadata") or {},
                "checks": checks_by_alpha.get(alpha_id, []),
            }
        )
    return output


def _ineligibility_reasons(
    run: dict[str, Any],
    state_counts: Counter[str],
    identities: Any,
    *,
    assigned_count: int,
    result_count: int,
) -> list[str]:
    reasons = []
    if run.get("state") not in {"COMPLETED", "COMPLETED_WITH_ERRORS"}:
        reasons.append(f"run_state_{str(run.get('state')).lower()}")
    for state in ("SIMULATE_UNKNOWN", "CANCELLED"):
        if state_counts.get(state):
            reasons.append(f"experiment_state_{state.lower()}")
    if assigned_count == 0:
        reasons.append("empty_run")
    if state_counts.get("READY", 0) != result_count:
        reasons.append("ready_result_count_mismatch")
    if any(
        identity.get("template_name") == "UNASSIGNED"
        or identity.get("template_family_id") is None
        or identity.get("template_version") is None
        or identity.get("template_epoch") is None
        for identity in identities
    ):
        reasons.append("template_lineage_missing")
    return reasons


def _family_assessments(
    performance: list[dict[str, Any]],
    checks: list[dict[str, Any]],
    representatives: list[dict[str, Any]],
    *,
    expansion_screen_eligible: bool,
) -> list[dict[str, Any]]:
    checks_by_key: dict[str, list[dict[str, Any]]] = defaultdict(list)
    representatives_by_key: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in checks:
        checks_by_key[str(row["key"])].append(row)
    for row in representatives:
        representatives_by_key[str(row["key"])].append(row)

    output = []
    for row in performance:
        key = str(row["key"])
        assigned = int(row["assigned_count"])
        ready = int(row["ready_count"])
        no_trade = int(row["no_trade_count"])
        check_rows = checks_by_key.get(key, [])
        fail_count = sum(item["status_counts"]["FAIL"] for item in check_rows)
        error_count = sum(item["status_counts"]["ERROR"] for item in check_rows)
        sharpe = row["metrics"]["sharpe"]
        best_sharpe = next(
            (
                item
                for item in representatives_by_key.get(key, [])
                if item["metric"] == "sharpe"
            ),
            None,
        )
        if ready == 0:
            evaluation = f"分配 {assigned} 条，READY 0 条；该模板没有可统计回测结果。"
            finding = "无法评价收益质量或相关性，必须保留为无结果模板。"
            improvement = "先修复 execution、字段、单位或 operator 契约，再创建新 epoch。"
        else:
            evaluation = (
                f"分配 {assigned} 条，READY {ready} 条，无交易 {no_trade} 条；"
                f"checks FAIL {fail_count}、ERROR {error_count}。"
            )
            finding = (
                f"Sharpe 中位数 {_display_value(sharpe['50%'])}，"
                f"有符号最大值 {_display_value(sharpe['max'])}；"
                f"代表 alpha {(best_sharpe or {}).get('alpha_id') or '无'}。"
            )
            if expansion_screen_eligible:
                improvement = "结合预注册密度门槛和 IS-PnL cluster 决策，不按单个极值扩展。"
            else:
                improvement = "当前 run 只允许描述性分析；修复完整性问题后用新 run 重测。"
        output.append(
            {
                "key": key,
                "template_name": row["template_name"],
                "template_name_zh": row["template_name_zh"],
                "template_logic_zh": row["template_logic_zh"],
                "evaluation": evaluation,
                "finding": finding,
                "improvement": improvement,
            }
        )
    return output


def _performance_csv(rows: list[dict[str, Any]]) -> str:
    header = ["template", "metric", "count", "mean", "std", "min", "25%", "50%", "75%", "max"]
    data = []
    for row in rows:
        for metric, stats in row["metrics"].items():
            data.append([row["template"], metric, *[stats[column] for column in header[2:]]])
    return _csv(header, data)


def _checks_csv(rows: list[dict[str, Any]]) -> str:
    header = [
        "template",
        "name",
        *_CHECK_STATUSES,
        "count",
        "mean",
        "std",
        "min",
        "25%",
        "50%",
        "75%",
        "max",
        "limitValues",
    ]
    data = []
    for row in rows:
        stats = row["value"]
        data.append(
            [
                row["template"],
                row["name"],
                *[row["status_counts"][status] for status in _CHECK_STATUSES],
                *[stats[column] for column in header[7:-1]],
                json.dumps(row["limitValues"], ensure_ascii=False, separators=(",", ":")),
            ]
        )
    return _csv(header, data)


def _representatives_csv(rows: list[dict[str, Any]]) -> str:
    header = [
        "metric",
        "template",
        "selection_scope",
        "alpha_id",
        "experiment_id",
        "regular_code",
        "sharpe",
        "fitness",
        "turnover",
        "margin",
        "returns",
        "drawdown",
        "pnl",
        "checks",
    ]
    data = [
        [
            row.get("metric"),
            row.get("template"),
            row.get("selection_scope"),
            row.get("alpha_id"),
            row.get("experiment_id"),
            row.get("regular_code"),
            row.get("sharpe"),
            row.get("fitness"),
            row.get("turnover"),
            row.get("margin"),
            row.get("returns"),
            row.get("drawdown"),
            row.get("pnl"),
            json.dumps(row.get("checks") or [], ensure_ascii=False, separators=(",", ":")),
        ]
        for row in rows
    ]
    return _csv(header, data)


def _csv(header: list[str], rows: list[list[Any]]) -> str:
    stream = io.StringIO()
    writer = csv.writer(stream, lineterminator="\n")
    writer.writerow(header)
    for row in rows:
        writer.writerow([_display_value(value) for value in row])
    return stream.getvalue()


def _display_value(value: Any) -> Any:
    if isinstance(value, float):
        return format(value, ".12g")
    return "" if value is None else value


def _finite_float(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


__all__ = [
    "TEMPLATE_FORMAT_VERSION",
    "TEMPLATE_REPORT_FORMAT_VERSION",
    "TemplateHeader",
    "build_template_report",
    "calculation_hash",
    "expression_hash",
    "parse_template_header",
    "render_template_report_markdown",
    "settings_hash",
    "validate_template_manifest",
]
