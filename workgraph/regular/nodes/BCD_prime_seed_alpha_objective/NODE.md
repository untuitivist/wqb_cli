# BCD' Seed Alpha / Objective

## Role

Replace B, C, and D when the user provides a specific `alpha_id` and an optimization objective.
This node anchors the run to an existing alpha instead of discovering a target tower from platform themes and pyramid status.
This node is executed by a nodesubagent only.

## Required Inputs

- Completed A node handoff.
- `node_input.json` with:
  - `extra.alpha_id`
  - `extra.optimization_objective`

## Required Outputs

- `outputs/seed_alpha.json`
- `outputs/optimization_objective.json`
- `outputs/decision.json`
- `outputs/seed_context.json`
- Required common output bundle.

## Process Requirements

1. Read `alpha_id` and `optimization_objective` only from `node_input.json`.
2. Fetch or inspect the seed alpha details when auth and API state allow it.
3. Derive the target tower from the seed alpha settings:
   - `region`
   - `delay`
   - `category` when available
4. If category is missing, infer it only from alpha metadata or fields and mark the confidence.
5. Convert the optimization objective into structured constraints and target metrics.
6. Derive `implementation_mode` from the seed alpha language unless the user explicitly asks to change language.
   If the seed alpha language is PYTHON, set allowed datafield types to `["MATRIX"]`.
   If the seed alpha language is FASTEXPR, keep Python disabled unless the optimization objective explicitly requires Python Alpha.
7. Do not inspect unrelated platform themes.
8. Do not run broad pyramid selection.
9. Do not generate new expressions.

## decision.json Minimum Shape

```json
{
  "target_tower": {
    "region": "USA",
    "delay": 1,
    "category": "analyst"
  },
  "source": "BCD_prime_seed_alpha_objective",
  "seed_alpha_id": "abc123",
  "implementation_mode": {
    "primary": "FASTEXPR",
    "allow_python": false,
    "allowed_datafield_types": ["MATRIX", "VECTOR", "GROUP", "SCALAR"],
    "reason": "Derived from seed alpha language."
  },
  "optimization_objective": {
    "primary_goal": "improve fitness",
    "constraints": []
  },
  "tower_derivation": {
    "region_source": "seed_alpha.settings.region",
    "delay_source": "seed_alpha.settings.delay",
    "category_source": "seed_alpha.category",
    "confidence": "high"
  },
  "why_this_tower": "The run is explicitly anchored to the user-provided seed alpha.",
  "why_not_bcd_discovery": "The user supplied a seed alpha and objective, so B/C/D discovery is intentionally skipped."
}
```

## seed_context.json Minimum Shape

```json
{
  "mode": "seed_alpha_optimization",
  "seed_alpha_id": "abc123",
  "language": "FASTEXPR",
  "regular": "rank(...)",
  "settings": {},
  "known_metrics": {},
  "optimization_objective": {},
  "downstream_guidance": [
    "E should build candidate fields around the seed tower and seed field families.",
    "H should form mechanisms as controlled improvements to the seed alpha."
  ]
}
```

## Success Criteria

- `outputs/decision.json` can substitute for D output.
- `outputs/seed_context.json` gives H enough context to optimize around the seed alpha.
- The optimization objective is explicit and machine-readable.

## Block Conditions

- `alpha_id` is missing.
- `optimization_objective` is missing or too vague to structure.
- The seed alpha cannot yield a usable region and delay.
