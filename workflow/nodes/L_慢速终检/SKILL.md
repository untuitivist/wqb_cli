# L_Slow_Final_Check

## Goal
- Take `K`'s best submit-ready alphas and run a slower pre-submit gate.
- Aggregate submission check, self correlation, prod correlation, and powerpool correlation.
- Decide whether the workflow can move to `M` or must roll back from `L`.

## Inputs
- Latest `*_node_K_diagnosis/diagnosis__{REGION}_D{DELAY}_{CATEGORY}.json`
- Real `alpha_id` values from `K`
- Current tower triple: `region / delay / category`

## Outputs
- `slow_final_check__{REGION}_D{DELAY}_{CATEGORY}.json`
- `submission_candidates__{REGION}_D{DELAY}_{CATEGORY}.json`
- `node_summary.md`

## Rules
- Use `WQBRAIN` Python only.
- Use command-line `wqb_core` entrypoints rather than re-implementing API calls.
- Preserve `K` hard metrics as the first gate.
- Treat `REGULAR_SUBMISSION`, `MATCHES_PYRAMID`, and slower correlation checks as the final gate before `M`.
- If `L` is run without any `good_alpha` from `K`, produce a no-op style result instead of crashing.
