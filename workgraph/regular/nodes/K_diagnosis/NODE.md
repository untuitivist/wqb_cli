# K Diagnosis

## Role

Diagnose J results and recommend a graph branch for the workagent to decide.
This node is executed by a nodesubagent only.

## Required Inputs

- J `outputs/simulation_results.json`.
- J `outputs/resume_state.json` if J was degraded.
- I `outputs/expression_candidates.json`.

## Required Outputs

- `outputs/diagnosis.json`
- `outputs/survivors.json`
- `outputs/branch_recommendation.json`
- Required common output bundle.

## Process Requirements

1. Diagnose every candidate with either metrics or an explicit missing-result reason.
2. Separate hard pass/fail metrics from softer interpretation.
3. Recommend one of L, D, E, H, I, or BEST_K_BRANCH, but do not update graph state.
4. Preserve enough detail for a future H/I/E redo.

## Success Criteria

- `branch_recommendation.json` names one recommended next node and the reason.
- Survivors are ranked with metrics and caveats.

## Block Conditions

- J produced neither results nor a resumable state.
- Candidate identity cannot be linked back to I.
