# WQB Simulation CLI

`wqb sim` wraps simulation APIs.

## `wqb sim options`

Raw API:

```text
OPTIONS /simulations
```

Command:

```powershell
wqb sim options
```

## `wqb sim get`

Get a simulation status or final result. The command follows `Retry-After` until the final response or `--max-wait-seconds`.

Raw API:

```text
GET /simulations/{simulation_id}
```

Command:

```powershell
wqb sim get 2UnwIe7g5jEcCgDvI4GpqO --max-wait-seconds 900
```

## `wqb sim create`

Create a simulation and wait for the final result. For multi-simulation, child simulations are also waited and included under top-level `children`. The initial `201 Created` is only `201 Created, waiting for results...`.

Raw API:

```text
POST /simulations
```

Command:

```powershell
wqb sim create --input api_inventory/examples/simulation_regular_close.json --max-wait-seconds 900
```
