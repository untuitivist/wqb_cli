# Node IO Constraints

This graph uses one folder per node execution.
That folder is both the audit record and the handoff package for downstream nodes.

## Node Folder

```text
research_runs/run_YYYYMMDD_HHMMSS/nodes/NN_NODE_ID/
  node_input.json
  process_log.md
  evidence_index.json
  validation_report.json
  handoff.md
  node_result.json
  outputs/
```

## Input Rules

- The nodesubagent must read `node_input.json` first.
- The nodesubagent may read only:
  - `node_input.json`
  - contracts listed in `node_input.json.contracts`
  - upstream files listed in `node_input.json.upstream_artifacts`
  - read-only repo source needed to understand APIs or contracts
- Business evidence from prior nodes must come through `node_input.json.upstream_artifacts`.
- The nodesubagent must not use chat history as an implicit input.
- If a needed upstream file is not listed, the node must block or ask the workagent to schedule a corrected node input.

## Output Rules

- All node-owned outputs must be under the assigned node directory.
- Business outputs must be under `outputs/`.
- Required business outputs are declared in `node_input.json.node.required_outputs`.
- A node may write additional diagnostic files under `outputs/`, but must index them in `evidence_index.json`.
- A node must not write batch files, summaries, scripts, or temporary artifacts at the run root.
- A node must not write into another node directory.

## Evidence Rules

`evidence_index.json` must list:

- every upstream artifact read, with purpose
- every output written, with purpose and record count when applicable
- every external source used, with status
- every degraded/skipped source, with reason

Downstream nodes should trust files, not chat.
If a claim is not traceable through `evidence_index.json`, downstream nodes should treat it as unavailable.

## Result Rules

`node_result.json` must not claim success unless:

- all required common files exist
- all `node.required_outputs` exist
- final `validation_report.json` is not `started`
- `constraints_checked.*` values required by `node_output_contract.md` are true
- `evidence_index.json` indexes the meaningful inputs and outputs

The workagent validates this with:

```text
workgraph/regular/scripts/validate_node_bundle.py <run_dir> <node_dir>
```
