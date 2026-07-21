from __future__ import annotations

from dataclasses import dataclass
from itertools import permutations
from typing import Mapping, Sequence

from .expressions import ExpressionViolation, ValidatedCandidate


_VECTOR_REDUCERS = (
    "vec_avg",
    "vec_sum",
    "vec_max",
    "vec_min",
    "vec_stddev",
    "vec_range",
    "vec_count",
)


_NORMALIZERS = frozenset(
    {
        "group_rank",
        "group_zscore",
        "normalize",
        "quantile",
        "rank",
        "scale",
        "ts_quantile",
        "ts_rank",
        "ts_zscore",
        "zscore",
    }
)
_COSMETIC_ONLY = frozenset(
    {"abs", "log", "rank", "reverse", "scale", "sign", "signed_power", "winsorize"}
)
_RELATIONAL = frozenset(
    {
        "regression_neut",
        "ts_corr",
        "ts_covariance",
        "ts_regression",
        "vector_neut",
    }
)
_CONDITIONAL = frozenset({"if_else", "trade_when"})
_CHANGE = frozenset({"days_from_last_change", "ts_delta", "ts_delta_limit"})


@dataclass(frozen=True)
class StrategyProfile:
    template_id: str
    template_type: str
    strategy_family: str
    field_ids: tuple[str, ...]
    operator_names: tuple[str, ...]

    def as_dict(self) -> dict[str, object]:
        return {
            "template_id": self.template_id,
            "template_type": self.template_type,
            "strategy_family": self.strategy_family,
            "field_ids": list(self.field_ids),
            "operator_names": list(self.operator_names),
        }


def validate_research_strategy(candidate: ValidatedCandidate) -> StrategyProfile:
    """Reject syntactically valid expressions that do not test a research mechanism."""

    operators = tuple(candidate.operators)
    if not operators:
        raise ExpressionViolation(
            "research candidate requires a temporal, relational, group, or conditional operator"
        )
    normalizer_count = sum(operator in _NORMALIZERS for operator in operators)
    if normalizer_count > 1:
        raise ExpressionViolation("research candidate stacks equivalent normalization operators")
    if set(operators) <= _COSMETIC_ONLY:
        raise ExpressionViolation(
            "research candidate cannot be a raw-field, rank-only, or cosmetic-only transform"
        )

    return profile_research_strategy(candidate)


def profile_research_strategy(candidate: ValidatedCandidate) -> StrategyProfile:
    operators = tuple(candidate.operators)
    family = _strategy_family(operators)
    template_type = (
        "unary"
        if len(candidate.fields) == 1
        else "binary"
        if len(candidate.fields) == 2
        else "multivariate"
    )
    primary = next(
        (operator for operator in operators if operator not in _COSMETIC_ONLY),
        operators[0] if operators else "raw",
    )
    return StrategyProfile(
        template_id=f"{template_type}:{primary}",
        template_type=template_type,
        strategy_family=family,
        field_ids=tuple(candidate.fields),
        operator_names=operators,
    )


def strategy_catalog(
    operators: Mapping[str, Mapping[str, object]], *, field_count: int,
    field_types: Mapping[str, str] | None = None,
) -> list[dict[str, object]]:
    """Return only strategy shapes supported by the live operator inventory."""

    available = {name.lower() for name in operators}
    normalized_types = {
        name.strip().lower(): value.strip().upper()
        for name, value in (field_types or {}).items()
    }
    has_vector_fields = any(value == "VECTOR" for value in normalized_types.values())
    vector_reducer = next(
        (name for name in _VECTOR_REDUCERS if name in available), None
    )
    if has_vector_fields and vector_reducer is None:
        return []
    specs = (
        {
            "strategy_id": "change_delta",
            "template_type": "unary",
            "strategy_family": "change",
            "required_operators": ["ts_delta"],
            "windows": [22, 63, 126, 252],
            "shape": "ts_delta(a, window)",
            "expression_template": "ts_delta({a}, {window})",
        },
        {
            "strategy_id": "temporal_abnormality",
            "template_type": "unary",
            "strategy_family": "time_series",
            "required_operators": ["ts_zscore"],
            "windows": [22, 63, 126, 252],
            "shape": "ts_zscore(a, window)",
            "expression_template": "ts_zscore({a}, {window})",
        },
        {
            "strategy_id": "change_recency",
            "template_type": "unary",
            "strategy_family": "change",
            "required_operators": ["days_from_last_change"],
            "windows": [],
            "shape": "days_from_last_change(a)",
            "expression_template": "days_from_last_change({a})",
        },
        {
            "strategy_id": "relationship_correlation",
            "template_type": "binary",
            "strategy_family": "relational",
            "required_operators": ["ts_corr"],
            "windows": [22, 63, 126, 252],
            "shape": "ts_corr(a, b, window)",
            "expression_template": "ts_corr({a}, {b}, {window})",
        },
        {
            "strategy_id": "relationship_regression",
            "template_type": "binary",
            "strategy_family": "relational",
            "required_operators": ["ts_regression"],
            "windows": [63, 126, 252],
            "shape": "ts_regression(a, b, window)",
            "expression_template": "ts_regression({a}, {b}, {window})",
        },
        {
            "strategy_id": "conditional_regime",
            "template_type": "binary",
            "strategy_family": "conditional",
            "required_operators": ["if_else", "ts_mean"],
            "windows": [22, 63, 126],
            "shape": "if_else(b > ts_mean(b, window), a, -a)",
            "expression_template": "if_else({b} > ts_mean({b}, {window}), {a}, -{a})",
        },
    )
    result: list[dict[str, object]] = []
    for spec in specs:
        if spec["template_type"] == "binary" and field_count < 2:
            continue
        required = list(spec["required_operators"])
        if has_vector_fields and vector_reducer is not None:
            required.append(vector_reducer)
        if set(required) <= available:
            result.append(
                {
                    **spec,
                    "required_operators": list(dict.fromkeys(required)),
                    "vector_reducer": vector_reducer,
                }
            )
    return result


def materialize_strategy_templates(
    operators: Mapping[str, Mapping[str, object]],
    field_ids: Sequence[str],
    *,
    strategy_ids: Sequence[str] = (),
    limit: int = 10,
    field_types: Mapping[str, str] | None = None,
) -> list[dict[str, object]]:
    """Expand selected abstract strategy shapes into deterministic candidates."""

    if type(limit) is not int or limit <= 0:
        raise ValueError("limit must be a positive integer")
    fields = tuple(dict.fromkeys(field.strip() for field in field_ids if field.strip()))
    if not fields:
        raise ValueError("field_ids must contain a nonblank field")
    normalized_types = {
        name.strip().lower(): value.strip().upper()
        for name, value in (field_types or {}).items()
    }
    catalog = strategy_catalog(
        operators, field_count=len(fields), field_types=normalized_types
    )
    requested = {value.strip() for value in strategy_ids if value.strip()}
    if requested:
        catalog = [item for item in catalog if item["strategy_id"] in requested]

    buckets: list[list[dict[str, object]]] = []
    for spec in catalog:
        bucket: list[dict[str, object]] = []
        template = str(spec["expression_template"])
        windows = list(spec["windows"]) or [None]
        bindings = (
            ((field, None) for field in fields)
            if spec["template_type"] == "unary"
            else permutations(fields, 2)
        )
        bindings = tuple(bindings)
        for window in windows:
            for primary, secondary in bindings:
                rendered_template = template
                reducer = spec.get("vector_reducer")
                if normalized_types.get(primary.lower()) == "VECTOR":
                    rendered_template = rendered_template.replace(
                        "{a}", f"{reducer}({{a}})"
                    )
                if (
                    secondary is not None
                    and normalized_types.get(secondary.lower()) == "VECTOR"
                ):
                    rendered_template = rendered_template.replace(
                        "{b}", f"{reducer}({{b}})"
                    )
                values = {"a": primary, "b": secondary, "window": window}
                expression = rendered_template.format(**values)
                field_bindings = {"a": primary}
                if secondary is not None:
                    field_bindings["b"] = secondary
                bucket.append(
                    {
                        "expression": expression,
                        "field_id": primary,
                        "single_mechanism": True,
                        "strategy_id": spec["strategy_id"],
                        "expression_template": rendered_template,
                        "field_bindings": field_bindings,
                        "materialization": "local_template_expansion",
                    }
                )
        if bucket:
            buckets.append(bucket)

    candidates: list[dict[str, object]] = []
    seen: set[str] = set()
    offset = 0
    while len(candidates) < limit:
        progressed = False
        for bucket in buckets:
            if offset >= len(bucket):
                continue
            progressed = True
            candidate = bucket[offset]
            expression = str(candidate["expression"])
            if expression in seen:
                continue
            seen.add(expression)
            candidates.append(candidate)
            if len(candidates) >= limit:
                return candidates
        if not progressed:
            break
        offset += 1
    return candidates


def _strategy_family(operators: tuple[str, ...]) -> str:
    names = set(operators)
    if names & _RELATIONAL:
        return "relational"
    if names & _CONDITIONAL:
        return "conditional"
    if names & _CHANGE:
        return "change"
    if any(name.startswith("group_") for name in names):
        return "group_relative"
    if any(name.startswith("ts_") for name in names):
        return "time_series"
    return "transformed"
