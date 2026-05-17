# L Slow Final Check

## Role

Perform bounded slow checks on K survivors before any submit action.
This node is executed by a nodesubagent only.

## Required Inputs

- K `outputs/survivors.json`.
- K `outputs/diagnosis.json`.

## Required Outputs

- `outputs/final_check_results.json`
- `outputs/approved_candidates.json`
- Required common output bundle.

## Process Requirements

1. Use only candidates approved by K.
2. Check correlation, pool value, and other slow gate evidence within budget.
3. Record missing or timed-out checks explicitly.
4. Use `workgraph/regular/alpha_improvement_guide.md` when interpreting settings robustness, PnL shape, concentration, and slow-check warnings.
5. Recommend M, D, or E through output only; do not branch directly.

## Success Criteria

- Every approved candidate has final-check evidence.
- M can prepare review-mode actions from approved candidates.

## Block Conditions

- K has no survivors.
- Slow checks cannot be run or bounded.
