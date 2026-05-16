# I Expression Candidates

## Role

Generate expression candidates from H mechanisms and E-allowed fields.
This node is executed by a nodesubagent only.
This node may generate REGULAR candidates in either FASTEXPR or PYTHON language.

## Required Inputs

- H `outputs/mechanism_hypotheses.json`.
- H `outputs/field_mechanism_map.json`.
- E `outputs/available_datafields.json`.
- D or BCD' `outputs/decision.json` for `implementation_mode`.

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
6. Generate PYTHON candidates only if D/BCD' `implementation_mode` allows Python.
7. For PYTHON candidates, follow `workgraph/regular/python_alpha_contract.md`.
8. For PYTHON candidates, run structural validation before writing `simulation_batch.json`:
   - source parses as Python
   - exactly one `@alpha(...)`
   - function parameters are exactly `(data, store)`
   - fields are accessed as attributes, not `data["field"]`
   - `lookback` is in settings, not in `@alpha(...)`
   - every declared field is present in E `available_datafields.json` with `type = "MATRIX"`
   - candidate is marked for single-alpha simulation, not parallel Python batch simulation
   - final output is cast to `np.float32`
9. Invalid PYTHON candidates must be written to `outputs/python_candidates.json` with failure reasons, but must not appear in `outputs/simulation_batch.json`.
10. Do not submit simulations directly unless this node contract is explicitly expanded.

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
It must use `data.field_id` style access and must not use `data["field_id"]`.
The decorator must not include `lookback`; use `settings.lookback`.
All fields in `data=[...]` must be MATRIX fields from E.
If a hypothesis needs non-MATRIX fields, emit only a FASTEXPR candidate or block that Python variant.
If D/BCD' did not enable Python, do not create Python candidates.

Use the validator with E's field library:

```text
python workgraph/regular/scripts/validate_python_alpha.py <candidate_json> --fields <E available_datafields.json> --require-matrix-fields
```

## Success Criteria

- Every candidate has id, language, type, regular payload, hypothesis id, field ids, and settings.
- Every PYTHON candidate passes the local structural and MATRIX-field checks in `python_alpha_contract.md`.
- `simulation_batch.json` is ready for J.

## Block Conditions

- Any expression uses a field not present in E.
- The only available implementation is for a different category.
- No valid expression can be generated.
- A PYTHON candidate cannot be represented as one self-contained code string.
