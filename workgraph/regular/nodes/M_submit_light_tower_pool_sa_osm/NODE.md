# M Submit / Light Tower / Pool / SA / OSM

## Role

Prepare or execute final actions for approved candidates.
This node is executed by a nodesubagent only.

## Required Inputs

- L `outputs/approved_candidates.json`.
- Workagent-provided mode: `review` by default, `live` only with explicit user instruction.

## Required Outputs

- `outputs/submission_plan.json`
- `outputs/submission_result.json`
- Required common output bundle.

## Process Requirements

1. Default to review mode.
2. In review mode, prepare actions but do not submit, light tower, move to pool, SA, or OSM.
3. In live mode, verify explicit user approval is present in `node_input.json`.
4. Record every action and response.

## Success Criteria

- Review mode produces a clear action plan.
- Live mode produces auditable action results.

## Block Conditions

- Live mode was requested without explicit user approval.
- No approved candidates are available.
