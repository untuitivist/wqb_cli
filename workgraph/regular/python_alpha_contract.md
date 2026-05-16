# Python Alpha Contract

Python alpha candidates are REGULAR alphas with `settings.language = "PYTHON"`.
They belong to the `workgraph/regular/` workgraph, not the future `workgraph/super/` workgraph.
In the current graph, Python alpha support is intentionally narrower than FASTEXPR:
Python alpha candidates are submitted as single-alpha simulations only, and every declared data field must be a MATRIX datafield.

## Payload Shape

```json
{
  "type": "REGULAR",
  "settings": {
    "language": "PYTHON",
    "instrumentType": "EQUITY",
    "region": "USA",
    "universe": "TOP3000",
    "delay": 1,
    "lookback": 5,
    "decay": 10,
    "neutralization": "MARKET",
    "pasteurization": "ON",
    "truncation": 0.08,
    "visualization": false,
    "maxPosition": "OFF",
    "maxTrade": "OFF"
  },
  "regular": "from brain.alphas import alpha\n..."
}
```

## Code Rules

- Include all imports and helper functions in the `regular` code string.
- Include exactly one `@alpha(...)` decorated function.
- The decorated function must accept exactly `(data, store)`.
- Declare every input field in `@alpha(data=[...])`.
- Every field declared in `@alpha(data=[...])` must appear in E `outputs/available_datafields.json` with `type = "MATRIX"`.
  Do not use VECTOR, GROUP, SCALAR, or table-shaped fields in Python alpha candidates until the PythonAlpha path is expanded.
- Do not pass `lookback` to `@alpha(...)`; lookback belongs in `settings.lookback`.
- Access fields as attributes such as `data.returns` or `data.close`.
  Do not use `data["returns"]` or other dictionary-style access.
- Do not include `universe` in `data`; it is always available as `data.universe`.
- Do not mutate data arrays in place; copy first when modifying.
- Return a one-dimensional `np.float32` array of shape `[n_instruments]`.
- Cast the final return with `.astype(np.float32)`.
- Use typed store declarations for persistent instrument-sized arrays when possible.

## Required Candidate Metadata

Every Python alpha candidate must include:

```json
{
  "id": "py_001",
  "language": "PYTHON",
  "type": "REGULAR",
  "hypothesis_id": "H1",
  "field_ids": ["returns"],
  "lookback": 5,
  "settings": {},
  "regular": "code string",
  "validation": {
    "has_alpha_decorator": true,
    "single_alpha_function": true,
    "returns_float32": true
  }
}
```

## Required Structural Checks

Before I passes a Python candidate downstream, it must record structural validation results for:

- parses with `ast.parse`
- exactly one decorated function with decorator name `alpha`
- decorated function has exactly two parameters named `data` and `store`
- `@alpha(...)` contains a `data=[...]` declaration
- `@alpha(...)` does not contain `lookback=...`
- source does not use dictionary-style `data[...]` access
- source returns or explicitly casts with `.astype(np.float32)`

The nodesubagent may use:

```text
workgraph/regular/scripts/validate_python_alpha.py <candidate_json_or_py>
```

## J-Node Handling

J submits Python alpha payloads through the single-alpha `wqb_core.simulation.simulate` source script.
Do not send Python alpha payloads through the parallel/concurrent batch path.
J must preserve the full source code string in its submitted payload artifact.
J must not run unbounded remote simulations; use the workagent budget.
