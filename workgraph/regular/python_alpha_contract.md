# Python Alpha Contract

Python alpha candidates are REGULAR alphas with `settings.language = "PYTHON"`.
They belong to the `workgraph/regular/` workgraph, not the future `workgraph/super/` workgraph.

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

## J-Node Handling

J submits Python alpha payloads through the same `wqb_core.simulation.simulate` path as FASTEXPR.
J must preserve the full source code string in its submitted payload artifact.
J must not run unbounded remote simulations; use the workagent budget.
