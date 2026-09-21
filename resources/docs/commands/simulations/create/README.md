# simulations create

Create a simulation and wait for the final platform result.

`simu` is an alias of `sim`. `--dry-run` validates and previews the payload without a simulation request.

REGION_AGNOSTIC uses one JSON object with `type: REGION_AGNOSTIC`, a `regular` expression and ALL/D1 settings with LARGE, MEDIUM or SMALL universe. Arrays containing ALL are rejected before HTTP. Completion resolves the RA_PARENT Alpha, then each regional RA_CHILD detail and PnL under `region_agnostic`; the parent has no PnL. Child Alpha IDs must not be polled as child simulation IDs. The simulation receipt remains in the output if child collection fails.

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
- `SUPER`: one SUPER request per simulation.
- `REGION_AGNOSTIC`: one parent object per request; ALL is not supported in HTTP batch arrays.
- Current simulation capacity is controlled by BRAIN's 429 / Retry-After responses. The CLI does not impose a fixed number of simulation slots.

Examples:

- `examples/backtest_modes.md`: REGULAR FASTEXPR single, REGULAR FASTEXPR multi, REGULAR PYTHON single, and SUPER single.
- `examples/input_json.md`: input JSON bodies for those modes.
