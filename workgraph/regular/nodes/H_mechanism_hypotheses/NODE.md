# H Economic Mechanism Hypotheses

## Role

Convert B/D/E/F/G evidence into a small set of economic mechanism hypotheses.
This node is executed by a nodesubagent only.

## Required Inputs

- B `outputs/theme_context.json`, or BCD' `outputs/seed_context.json`.
- D `outputs/decision.json`, or BCD' `outputs/decision.json`.
- E `outputs/available_datafields.json`.
- F `outputs/community_experience.json`.
- G `outputs/external_material_summary.json`.

## Required Outputs

- `outputs/mechanism_hypotheses.json`
- `outputs/field_mechanism_map.json`
- Required common output bundle.

## Process Requirements

1. Use only fields present in E output.
2. Keep degraded G evidence separate from positive external support.
3. Rank hypotheses by mechanism clarity and field feasibility.
4. Do not hard-code analyst fields when the D category is not analyst.
5. Do not generate alpha expressions.
6. In BCD' mode, form mechanisms as controlled improvements to the seed alpha and objective, not as broad tower discovery.

## Success Criteria

- Every hypothesis references field ids that exist in E output.
- The handoff tells I which field families are allowed.

## Block Conditions

- E candidate pool is empty.
- A hypothesis requires fields absent from E output.
- BCD' mode is active but seed context or optimization objective is missing.
