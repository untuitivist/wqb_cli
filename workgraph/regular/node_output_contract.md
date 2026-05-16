# Node Output Contract

Every nodesubagent must create this bundle inside its assigned node directory.
The workagent uses these files to supervise the node and the next nodesubagent uses them as upstream context.

## Required Layout

```text
NN_NODE_ID/
  node_input.json
  process_log.md
  evidence_index.json
  validation_report.json
  handoff.md
  node_result.json
  outputs/
```

## Startup Files

Before any network request, API polling, simulation, broad source inspection, or long-running command, the nodesubagent must write minimal startup evidence:

- `process_log.md` with `started_at`, node id, assigned node directory, and intended first action.
- `validation_report.json` with `status = "started"` and a `write_scope_only_node_dir` check.

These files are not optional.
They let the workagent distinguish a stuck nodesubagent from a node that never started.

## process_log.md

Record the actual work sequence.
Include:

- inputs opened
- commands or scripts run
- important intermediate observations
- checks performed
- failures, retries, and degraded paths

Do not write only conclusions.

## evidence_index.json

Index every meaningful input and output:

```json
{
  "inputs_read": [
    {
      "path": "research_runs/run_.../nodes/04_D_main_tower/outputs/decision.json",
      "purpose": "target tower"
    }
  ],
  "outputs_written": [
    {
      "path": "outputs/available_datafields.json",
      "purpose": "candidate field pool",
      "record_count": 42
    }
  ],
  "external_sources": [
    {
      "source": "worldquantbrain",
      "status": "success"
    }
  ]
}
```

Paths under `outputs_written` should be relative to the assigned node directory when possible.

## validation_report.json

Write machine-readable checks:

```json
{
  "status": "passed",
  "checks": [
    {
      "name": "write_scope_only_node_dir",
      "status": "passed",
      "details": null
    },
    {
      "name": "required_inputs_present",
      "status": "passed",
      "details": null
    }
  ]
}
```

Use `failed` for any check that should block downstream use.
Use `warning` for degraded but usable optional evidence.
The final `validation_report.json` status must be one of `passed`, `warning`, or `failed`.
`started` is allowed only while the node is still running.

## handoff.md

Write for the next nodesubagent.
Include:

- concise state summary
- exact output files to read next
- assumptions that must not be silently changed
- degraded or missing evidence
- recommended downstream caution

Do not decide the graph branch.

## node_result.json

Write final status:

```json
{
  "node_id": "E_data_and_field_feasibility",
  "status": "success",
  "blocking_reason": null,
  "next_recommendation": null,
  "outputs": {
    "primary": "outputs/available_datafields.json"
  },
  "constraints_checked": {
    "write_scope_only_node_dir": true,
    "used_required_inputs": true,
    "process_log_complete": true,
    "evidence_index_complete": true,
    "validation_report_complete": true,
    "handoff_complete": true
  },
  "notes": []
}
```

Allowed status values are `success`, `blocked`, `degraded`, and `failed`.

`node_result.json` is invalid unless:

- `node_id` matches the assigned node id in `node_input.json`.
- `constraints_checked.write_scope_only_node_dir` is `true`.
- `constraints_checked.process_log_complete` is `true`.
- `constraints_checked.evidence_index_complete` is `true`.
- `constraints_checked.validation_report_complete` is `true`.
- `constraints_checked.handoff_complete` is `true`.
- The final `validation_report.json` is not `status = "started"`.
