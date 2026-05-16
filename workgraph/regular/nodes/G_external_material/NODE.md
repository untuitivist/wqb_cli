# G External Material

## Role

Collect external papers or user-provided material relevant to the selected tower and field pool.
This node is executed by a nodesubagent only.

## Required Inputs

- D `outputs/decision.json`, or BCD' `outputs/decision.json`.
- E `outputs/available_datafields.json`.

## Required Outputs

- `outputs/external_queries.json`
- `outputs/external_material_summary.json`
- Required common output bundle.

## Process Requirements

1. Build search queries from D tower and E field families.
2. Use bounded searches and record source status.
3. If an external source returns 429, timeout, or network failure, write a degraded summary with the failure reason.
4. Do not block H only because optional external search failed.
5. Do not invent external evidence.

## Success Criteria

- `external_material_summary.json` exists in both success and degraded cases.
- H can distinguish positive evidence from unavailable evidence.

## Block Conditions

- Required D/BCD' or E outputs are missing.
- The node cannot write a truthful degraded summary.
