# D Main Tower

## Role

Choose exactly one target tower from B and C evidence.
This node is executed by a nodesubagent only.

## Required Inputs

- B `outputs/theme_context.json`.
- C `outputs/pyramid_summary.json`.
- B and C handoff files.

## Required Outputs

- `outputs/decision.json`
- `outputs/tower_candidates.json`
- Required common output bundle.

## Process Requirements

1. Use C point-lighting status as the first priority.
2. Enforce hard category constraints before theme preference.
3. Prefer mature non-D0 towers when point-lighting priority is tied.
4. Explain why the selected tower beats the second choice.
5. Do not inspect dataset or datafield pools.
6. Do not generate expressions.

## decision.json Minimum Shape

```json
{
  "target_tower": {
    "region": "USA",
    "delay": 1,
    "category": "pv"
  },
  "second_choice": {},
  "lighting_priority_judgment": "",
  "category_concentration_judgment": "",
  "vertical_maturity_judgment": "",
  "d0_avoidance_judgment": "",
  "why_this_tower": "",
  "why_not_second_choice": ""
}
```

## Success Criteria

- Exactly one tower is selected.
- The output can drive E/F/G/H without extra user steering.

## Block Conditions

- B or C evidence is missing.
- No unique tower can be selected from allowed evidence.
