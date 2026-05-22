# simulations create

Create a simulation and wait for the final platform result.

Command:

```powershell
wqb sim create --input <input.json> --output <output.json>
```

Default wait cap:

```powershell
wqb sim create --input <input.json> --max-wait-seconds 900 --output <output.json>
```

`sim create` now returns only after the simulation has a final result or the wait fails/times out. The initial `201 Created` is preserved under `create` and classified as:

```text
201 Created, waiting for results...
```

That `201` means the API accepted the request and created a simulation resource. It is not final backtest success and it is not proof that an alpha was generated.

Final success is determined by the waited result:

- `classification.status = COMPLETE` means the simulation finished normally.
- `classification.status = WARNING` means the simulation finished with platform warnings; if `alpha` is present, the alpha was generated.
- `classification.status = ERROR`, `FAIL`, or `FAILED` means platform execution failed.
- `classification.reason = simulation_wait_timed_out` means the CLI reached `--max-wait-seconds` before a final result.
- For multi-simulation, the parent can finish with `children`; `sim create` also waits for those child simulations and includes them under top-level `children`.

Parallel and batch constraints:

- `REGULAR_FASTEXPR_MULTI`: max 10 expressions in one request. Use 10 outside `GLB`, 5 for `GLB`.
- `REGULAR_PYTHON`: no multi-simulation; one expression per request.
- `SUPER`: one SUPER request per simulation; external concurrency max 3.
- External REGULAR concurrency: max 8 outside `GLB`, max 4 for `GLB`.

Examples:

- `examples/backtest_modes.md`: REGULAR FASTEXPR single, REGULAR FASTEXPR multi, REGULAR PYTHON single, and SUPER single.
- `examples/input_json.md`: input JSON bodies for those modes.
