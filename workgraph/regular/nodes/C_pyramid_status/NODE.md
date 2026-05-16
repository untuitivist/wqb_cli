# C Pyramid Status

## Role

Collect pyramid status for current-quarter and all-time tower selection.
This node is executed by a nodesubagent only.

## Required Inputs

- Completed A node handoff.
- `node_input.json`.

## Required Outputs

- `outputs/current_quarter_pyramids.json`
- `outputs/all_pyramids.json`
- `outputs/pyramid_summary.json`
- Required common output bundle.

## Process Requirements

1. Read A handoff and confirm auth is usable.
2. Collect current-quarter and all-time pyramid counts.
3. Normalize tower keys as `REGION/D<delay>/<category>`.
4. Preserve raw counts and derived fields separately.

## Success Criteria

- D can compare towers without reading chat history.
- `pyramid_summary.json` includes current count, all-time count, and remaining slots to 3.

## Block Conditions

- Current-quarter status is unavailable.
- Tower keys cannot be normalized.
