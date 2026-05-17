# K Diagnosis

## Role

Diagnose J results and recommend a graph branch for the workagent to decide.
This node is executed by a nodesubagent only.

## Required Inputs

- J `outputs/simulation_results.json`.
- J `outputs/resume_state.json` if J was degraded.
- I `outputs/expression_candidates.json`.
- BCD' `outputs/optimization_objective.json` when the run is seed-alpha optimization.
- D or BCD' `outputs/decision.json` when objective-specific thresholds are present.

## Required Outputs

- `outputs/metric_policy.json`
- `outputs/diagnosis.json`
- `outputs/survivors.json`
- `outputs/rejected_candidates.json`
- `outputs/branch_recommendation.json`
- Required common output bundle.

## Process Requirements

1. Diagnose every candidate with either metrics or an explicit missing-result reason.
2. Separate hard pass/fail metrics from softer interpretation.
3. Build `metric_policy.json` before ranking candidates.
4. Apply hard gates first; do not promote a candidate to L only because the narrative is promising.
5. Recommend one of L, D, E, H, I, or BEST_K_BRANCH, but do not update graph state.
6. Preserve enough detail for a future H/I/E redo.

## Metric Policy

K must use this precedence order:

1. User-provided `optimization_objective` thresholds.
2. Platform `submission_check` results when an `alpha_id` is available.
3. BCD' seed-alpha objective thresholds.
4. Workagent-provided thresholds in `node_input.json.extra.metric_policy`.
5. The fallback policy below.

Fallback hard gates for a candidate to survive to L when platform checks are not yet available:

```json
{
  "min_sharpe": 1.58,
  "target_sharpe": 2.0,
  "min_fitness": 1.0,
  "target_fitness": 1.5,
  "min_turnover": 0.10,
  "max_turnover": 0.40,
  "target_turnover_min": 0.10,
  "target_turnover_max": 0.15,
  "max_prod_corr": 0.7,
  "target_prod_corr": 0.5,
  "max_self_corr": 0.7,
  "target_self_corr": 0.5,
  "min_margin": 0.001,
  "require_simulation_status": ["COMPLETE", "PASS", "SUCCESS"],
  "allow_missing_optional_metrics": false
}
```

These fallback values are the graph's default K-screening policy.
They are stricter than the basic tutorial examples for Sharpe and turnover because the graph is optimizing for usable, high-quality candidates.
When `submission_check` is available, K must record the platform check payload and treat platform pass/fail as authoritative.
Metrics such as drawdown, returns, and long/short count are diagnostic or objective-specific unless the platform check marks them as hard failures.
Margin is a hard K-screening metric: require more than `0.1%` (`0.001`) and rank larger margin higher.
K must preserve the raw metric value and unit when J/platform output is ambiguous, then add a normalized decimal value used for gating.
For example, `0.1%` must be normalized to `0.001`.

Interpret hard gates and target bands separately:

- Hard pass requires `sharpe >= 1.58`, `fitness >= 1.0`, `0.10 <= turnover <= 0.40`, `prod_corr <= 0.7`, `self_corr <= 0.7`, and `margin > 0.001`.
- Strong pass / preferred survivor should aim for `sharpe >= 2.0`, `fitness >= 1.5`, `0.10 <= turnover <= 0.15`, `prod_corr < 0.5`, `self_corr < 0.5`, and higher margin.
- A candidate that passes hard gates but misses preferred targets remains a survivor, but K must label the missed targets as soft caveats.

## Understand Results Rules

K must interpret IS results using these definitions and diagnostics:

- `Sharpe` measures risk-adjusted PnL stability.
  Low Sharpe usually means weak signal, excessive volatility, or a noisy mechanism.
- `Turnover = DollarTradingValue / Booksize`.
  Platform examples use a broad pass band of roughly 1% to 70%, but this workgraph's K policy is stricter: prefer roughly 10% to 15%, allow 10% to 40%.
- `Fitness = Sharpe * sqrt(abs(Returns) / max(Turnover, 0.125))`.
  Fitness can be improved by increasing Sharpe/Returns or lowering excessive turnover.
- `Returns` is annualized return and is diagnostic unless the objective explicitly sets a threshold.
- `Drawdown` is the largest peak-to-trough PnL gap normalized by book size.
  It is diagnostic unless the platform check or objective marks it as hard failure.
- `Margin = PnL / TotalDollarsTraded`.
  K requires margin above 0.1% and ranks higher margin better.

K must also record platform/test warnings:

- Syntax or operator errors should branch to `I_expression_candidates`.
- Incompatible unit warnings should usually branch to `I_expression_candidates` unless the warning is known to be harmless and platform allows submission.
- Weight concentration warnings should identify whether the issue is expression scaling/truncation or field concentration.
- Sub-universe Sharpe failures should record the sub-universe threshold evidence and usually branch to `H_mechanism_hypotheses`, `E_data_and_field_feasibility`, or `I_expression_candidates` depending on whether the cause is mechanism, field pool, or expression construction.
- A cumulative PnL chart with large drawdowns, sharp one-day loss, or unstable regime behavior should be a soft or hard caveat depending on severity, even when numeric gates pass.

For seed-alpha optimization, objective constraints override defaults.
For example, if the user says `prod_corr < 0.5` and `Sharpe >= 2.1`, K must encode:

```json
{
  "min_sharpe": 2.1,
  "max_prod_corr": 0.5
}
```

If a metric is missing:

- Missing required hard metric means the candidate is not a survivor.
- Missing optional diagnostic metric may be recorded as caveat only if `allow_missing_optional_metrics = true`.
- If all candidates have missing required metrics because J did not return usable results, K must return `blocked` or branch back to J via `BEST_K_BRANCH` only when the graph supports a bounded J retry.

## Candidate Classification

Every candidate must be classified as exactly one of:

- `hard_pass`: passes all hard gates.
- `soft_pass`: fails no critical objective gate but has missing optional diagnostics or weak secondary quality.
- `hard_fail`: fails at least one hard gate.
- `missing_result`: cannot be scored from J output.

Only `hard_pass` candidates can be sent to L by default.
`soft_pass` may go to L only when `metric_policy.allow_soft_pass_to_L = true` and the caveat is explicit.

## Branch Rules

- Recommend `L_slow_final_check` when at least one `hard_pass` survivor exists.
- Recommend `I_expression_candidates` when failures are mostly expression/operator/parameter issues.
- Recommend `H_mechanism_hypotheses` when failures show weak economic mechanism, unstable signal, or repeated low Sharpe/fitness.
- Recommend `E_data_and_field_feasibility` when failures point to bad field family, missing MATRIX subset, reused fields, or field crowding.
- Recommend `D_main_tower` when the selected tower has no viable field/mechanism path or hard objective conflicts with the tower.
- Recommend `BEST_K_BRANCH` only when a bounded J retry/resume is the best next action and `resume_state.json` is usable.

## diagnosis.json Minimum Shape

```json
{
  "metric_policy_source": "optimization_objective",
  "candidate_diagnostics": [
    {
      "candidate_id": "expr_001",
      "classification": "hard_fail",
      "metrics": {
        "sharpe": {"raw": 1.9, "normalized": 1.9},
        "fitness": {"raw": 0.72, "normalized": 0.72},
        "prod_corr": {"raw": 0.56, "normalized": 0.56},
        "self_corr": {"raw": 0.31, "normalized": 0.31},
        "turnover": {"raw": "42%", "normalized": 0.42},
        "drawdown": {"raw": "18%", "normalized": 0.18},
        "margin": {"raw": "0.08%", "normalized": 0.0008}
      },
      "failed_hard_gates": ["min_sharpe", "max_prod_corr"],
      "missed_preferred_targets": ["target_prod_corr", "target_turnover_max", "target_margin"],
      "platform_warnings": [],
      "pnl_shape_diagnosis": "not_inspected",
      "soft_caveats": ["turnover is outside preferred band"],
      "recommended_repair": {
        "node": "I_expression_candidates",
        "reason": "prod_corr remains above objective; try less linear transform or alternate field combination"
      }
    }
  ]
}
```

## Success Criteria

- `metric_policy.json` records the exact hard thresholds used and their source.
- Every candidate is classified against hard gates.
- `branch_recommendation.json` names one recommended next node and the reason.
- Survivors are ranked with metrics, failed-gate evidence, and caveats.
- Rejected candidates include failed hard gates or missing-result reasons.

## Block Conditions

- J produced neither results nor a resumable state.
- Candidate identity cannot be linked back to I.
- Required hard metrics cannot be extracted for every candidate and no bounded J retry is available.
