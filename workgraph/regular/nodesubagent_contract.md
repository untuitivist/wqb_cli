# Nodesubagent Contract

Use this contract for a single WQB workgraph node.

## Hard Boundary

You may write only inside your assigned node directory:

```text
research_runs/run_YYYYMMDD_HHMMSS/nodes/NN_NODE_ID/
```

You may read prior artifacts inside the active run directory.
Do not create, edit, or delete files anywhere else.

## Required Files

Read:

- `node_input.json`
- upstream artifacts listed in `node_input.json`

On startup, before any action that can block, write:

- `process_log.md`
- `validation_report.json`

Use the startup format required by `workgraph/regular/node_output_contract.md`.

Write:

- `node_result.json`
- `process_log.md`
- `evidence_index.json`
- `handoff.md`
- `validation_report.json`
- any node outputs under `outputs/`

## Forbidden

- Do not edit source code.
- Do not write into `workflow/`, `workgraph/`, `docs/`, `wqb_core/`, or repo root.
- Do not create another run directory.
- Do not run later nodes.
- Do not decide the graph branch.
- Do not invent upstream artifacts.
- Do not hide failed checks in prose. Put them in `validation_report.json` and `node_result.json`.
- Do not write a summary-only node. The next nodesubagent must be able to continue from your files without reading chat history.
- Do not leave `validation_report.json` in `started` status when finishing.
- Do not claim `success` when required output files are missing.
- Do not continue from chat history. Use `node_input.json` and upstream artifacts only.

## Result Rules

Use `status=blocked` when required inputs are missing or impossible.
Use `status=degraded` when optional evidence is unavailable but the node can produce a valid downstream artifact.
Use `status=failed` only when execution failed and no valid downstream artifact exists.

Always explain the issue in `blocking_reason` for `blocked` or `failed`.

Follow `workgraph/regular/node_output_contract.md` exactly.
