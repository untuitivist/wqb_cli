# D Main Tower

## Role

Choose exactly one target tower from B and C evidence.
Choose the implementation mode before E runs, so E can filter datafield types correctly.
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

1. Use point-lighting as the first priority.
2. Within point-lighting candidates, serve the user's durable objective: high VF, higher weight, and GM readiness.
3. Prefer towers that can plausibly produce many distinct, low-correlation, post-cost-valid regular alphas.
4. Prefer mature D1 towers when point-lighting priority is tied or when D0 adds unnecessary fragility.
5. Prefer categories with broad mechanism depth and likely field supply.
6. Penalize crowded categories when B/C evidence suggests high reuse, high production correlation risk, or weak uniqueness.
7. Enforce hard category constraints before theme preference.
8. Explain why the selected tower beats the second choice.
9. Do not inspect dataset or datafield pools directly; leave hard field feasibility to E.
10. Choose `implementation_mode` as `FASTEXPR`, `PYTHON`, or `MIXED`.
    Use `PYTHON` only when the intended research direction needs Python Alpha state/helpers and can work with MATRIX datafields only.
    Use `FASTEXPR` when non-MATRIX fields may be important or when the idea is expressible with platform operators.
11. Do not generate expressions.

## Tower Selection Priority

Use this order when ranking towers:

1. **Hard viability**: region, delay, and category must be valid for REGULAR alpha work and compatible with available auth/platform state.
2. **Point-lighting value**: current-quarter count, remaining slots to 3, multiplier, and all-time coverage.
3. **GM/VF/weight fit**: among point-lighting candidates, category should support quality, diversity, uniqueness, low correlation, and post-cost robustness.
4. **Field-supply prior**: before E checks exact fields, prefer categories historically likely to have enough clean fields and mechanisms.
5. **Crowding risk**: avoid towers likely dominated by reused fields, common templates, or high prod-corr patterns.
6. **Theme/platform fit**: use B themes as a tie-breaker when the above are close.

If two towers have meaningfully different point-lighting value, choose the better point-lighting tower unless it violates hard viability.
If point-lighting value is tied or close, use GM/VF/weight fit, field-supply prior, and crowding risk to break the tie.

## decision.json Minimum Shape

```json
{
  "target_tower": {
    "region": "USA",
    "delay": 1,
    "category": "pv"
  },
  "implementation_mode": {
    "primary": "FASTEXPR",
    "allow_python": false,
    "allowed_datafield_types": ["MATRIX", "VECTOR", "GROUP", "SCALAR"],
    "reason": "FASTEXPR is the default unless Python-specific mechanics are needed before E."
  },
  "second_choice": {},
  "lighting_priority_judgment": "",
  "category_concentration_judgment": "",
  "vertical_maturity_judgment": "",
  "d0_avoidance_judgment": "",
  "objective_alignment_judgment": "",
  "field_supply_prior_judgment": "",
  "crowding_risk_judgment": "",
  "theme_fit_judgment": "",
  "expected_downstream_burden": "",
  "why_this_tower": "",
  "why_not_second_choice": ""
}
```

## Success Criteria

- Exactly one tower is selected.
- Implementation mode is selected before E.
- The output can drive E/F/G/H without extra user steering.

## Block Conditions

- B or C evidence is missing.
- No unique tower can be selected from allowed evidence.
