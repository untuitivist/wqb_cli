# M_Submit_Light_Tower_Pool_SA_OSM

## Goal
- Turn `L` approved alphas into explicit submission actions.
- Support a safe default review mode and an explicit execute mode.

## Inputs
- Latest `*_node_L_slow_final_check/submission_candidates__{REGION}_D{DELAY}_{CATEGORY}.json`
- Optional alpha property metadata
- Current tower triple: `region / delay / category`

## Outputs
- `submission_actions__{REGION}_D{DELAY}_{CATEGORY}.json`
- `submit_results__{REGION}_D{DELAY}_{CATEGORY}.json`
- `node_summary.md`

## Rules
- Default to `review` mode.
- Only execute actual submit calls in explicit `execute` mode.
- Keep writes inside Python scripts.
- Preserve a complete record of what was planned versus what was executed.
