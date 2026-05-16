# B Theme / Platform Opportunities

## Role

Collect current platform messages, events, and theme signals.
This node is executed by a nodesubagent only.

## Required Inputs

- Completed A node handoff.
- `node_input.json`.

## Required Outputs

- `outputs/theme_context.json`
- `outputs/messages_summary.json` when available.
- `outputs/events_summary.json` when available.
- Required common output bundle from `workgraph/regular/node_output_contract.md`.

## Process Requirements

1. Read A handoff and confirm auth is usable.
2. Fetch or summarize platform messages and events with bounded limits.
3. Separate raw evidence from interpretation.
4. Mark external/API fetch problems as `degraded` only if enough cached or partial evidence remains useful.

## Success Criteria

- Theme context includes source timestamps or fetch status.
- Handoff names which theme signals are strong, weak, or irrelevant.

## Block Conditions

- No auth and no usable local evidence.
- Outputs cannot identify their evidence source.
