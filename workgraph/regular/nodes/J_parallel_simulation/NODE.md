# J Parallel Simulation

## Role

Run a bounded simulation batch from I candidates.
This node is executed by a nodesubagent only.
This node supports REGULAR FASTEXPR and REGULAR PYTHON payloads.

## Required Inputs

- I `outputs/simulation_batch.json`.
- Workagent-provided budget in `node_input.json` such as max candidates, max wall time, and mode.

## Required Outputs

- `outputs/submitted_batch.json`
- `outputs/payloads/`
- `outputs/simulation_results.json`
- `outputs/resume_state.json`
- Required common output bundle.

## Process Requirements

1. Enforce the workagent budget before submitting anything.
2. Support dry-run or preview mode when requested.
3. Write partial results and `resume_state.json` before any long wait.
4. On timeout, return `status=degraded` if partial results are usable, otherwise `blocked`.
5. Do not loop indefinitely to chase a good alpha.
6. Route validation by `settings.language`.
7. Preserve every submitted payload exactly under `outputs/payloads/`.

## Language-Specific Validation

### FASTEXPR

- Require `type = "REGULAR"`.
- Require `settings.language = "FASTEXPR"`.
- Require `regular` to be a non-empty expression string.
- Require all field ids to have been accepted by I.

### PYTHON

- Require `type = "REGULAR"`.
- Require `settings.language = "PYTHON"`.
- Require `regular` to be a non-empty Python source string.
- Require exactly one `@alpha(...)` decorated function.
- Require `lookback` in settings.
- Preserve the full code string in the payload artifact.
- Do not execute local BrainLab simulations unless the workagent explicitly sets a local-debug mode.

## Success Criteria

- K can read simulation ids, alpha ids when available, candidate ids, and failure records.
- Timeout state is explicit and resumable.
- Submitted FASTEXPR and PYTHON payloads are distinguishable in `submitted_batch.json`.

## Block Conditions

- Missing simulation batch.
- No budget is provided.
- API state prevents any bounded execution or preview.
- A payload language is neither FASTEXPR nor PYTHON.
