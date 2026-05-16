# E Data and Field Feasibility

## Role

Build a reusable candidate dataset and datafield pool for the D-selected tower.
Apply the implementation mode selected by D or BCD' before screening datafields.
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

1. Read the target tower and `implementation_mode` only from D output or BCD' D-equivalent output.
2. Preserve the priority order:
   - OS-bad datasets must not be used.
   - Used datafields are forbidden.
   - Used datasets should preferably not be reused.
3. Use run-local outputs for every derived artifact.
4. Do not silently continue with an empty candidate field pool.
5. Preserve datafield `type` exactly.
6. If `implementation_mode.primary = "PYTHON"` or `implementation_mode.allow_python = true`, include a Python-usable field subset containing only `type = "MATRIX"`.
7. If `implementation_mode.primary = "PYTHON"`, block when the MATRIX field subset is empty.
8. If `implementation_mode.primary = "FASTEXPR"`, do not over-filter to MATRIX; keep all allowed field types unless excluded by OS/used-field rules.

## Success Criteria

- `available_datafields.json` has `candidate_count > 0`.
- Every candidate field includes dataset id, field id, type, and exclusion status.
- Every MATRIX candidate can be identified mechanically by I.
- If Python is enabled, `available_datafields.json` exposes the MATRIX-only subset or equivalent per-field `python_usable` flag.

## Block Conditions

- D decision is missing.
- Both D and BCD' decisions are missing.
- Candidate count is zero.
- `implementation_mode.primary = "PYTHON"` and no MATRIX candidates remain.
- Used-field exclusion cannot be checked.
