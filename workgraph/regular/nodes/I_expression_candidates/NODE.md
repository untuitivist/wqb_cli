# I Expression Candidates

## Role

Generate expression candidates from H mechanisms and E-allowed fields.
This node is executed by a nodesubagent only.
This node may generate REGULAR candidates in either FASTEXPR or PYTHON language.

## Required Inputs

- H `outputs/mechanism_hypotheses.json`.
- H `outputs/field_mechanism_map.json`.
- E `outputs/available_datafields.json`.

## Required Outputs

- `outputs/expression_candidates.json`
- `outputs/fastexpr_candidates.json`
- `outputs/python_candidates.json`
- `outputs/simulation_batch.json`
- Required common output bundle.

## Process Requirements

1. Validate every field used in every expression against E output.
2. Use category-appropriate expression templates.
3. If no template fits the selected category, block with a clear reason.
4. Keep expression rationale tied to H hypothesis ids.
5. For FASTEXPR candidates, validate operator parameters and keep the final expression in `regular`.
6. For PYTHON candidates, follow `workgraph/regular/python_alpha_contract.md`.
7. Do not submit simulations directly unless this node contract is explicitly expanded.

## Candidate Language Families

### FASTEXPR

FASTEXPR candidates use:

```json
{
  "type": "REGULAR",
  "language": "FASTEXPR",
  "settings": {
    "language": "FASTEXPR"
  },
  "regular": "rank(...)"
}
```

### PYTHON

PYTHON candidates use:

```json
{
  "type": "REGULAR",
  "language": "PYTHON",
  "settings": {
    "language": "PYTHON",
    "lookback": 5
  },
  "regular": "from brain.alphas import alpha\n..."
}
```

Python candidate source code must contain imports, helpers, and exactly one `@alpha(...)` decorated function in the same string.

## Success Criteria

- Every candidate has id, language, type, regular payload, hypothesis id, field ids, and settings.
- Every PYTHON candidate passes the local structural checks in `python_alpha_contract.md`.
- `simulation_batch.json` is ready for J.

## Block Conditions

- Any expression uses a field not present in E.
- The only available implementation is for a different category.
- No valid expression can be generated.
- A PYTHON candidate cannot be represented as one self-contained code string.
