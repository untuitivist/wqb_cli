# E Data and Field Feasibility

## Role

Build a reusable candidate dataset and datafield pool for the D-selected tower.
This node is executed by a nodesubagent only.

## Required Inputs

- D `outputs/decision.json`, or BCD' `outputs/decision.json`.
- Prior active-tower or field-exclusion evidence only if listed in `node_input.json`.

## Required Outputs

- `outputs/dataset_screening.json`
- `outputs/used_fields.json`
- `outputs/available_datafields.json`
- Required common output bundle.

## Process Requirements

1. Read the target tower only from D output or BCD' D-equivalent output.
2. Preserve the priority order:
   - OS-bad datasets must not be used.
   - Used datafields are forbidden.
   - Used datasets should preferably not be reused.
3. Use run-local outputs for every derived artifact.
4. Do not silently continue with an empty candidate field pool.

## Success Criteria

- `available_datafields.json` has `candidate_count > 0`.
- Every candidate field includes dataset id, field id, type, and exclusion status.

## Block Conditions

- D decision is missing.
- Both D and BCD' decisions are missing.
- Candidate count is zero.
- Used-field exclusion cannot be checked.
