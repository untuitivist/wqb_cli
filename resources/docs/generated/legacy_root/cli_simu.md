# WQB Simulation CLI

`wqb simu` wraps simulation APIs.

## `wqb simu options`

Raw API:

```text
OPTIONS /simulations
```

Command:

```powershell
wqb simu options
```

## `wqb simu get`

Get a simulation status or final result. The command follows `Retry-After` until the final response or `--max-wait-seconds`.

Raw API:

```text
GET /simulations/{simulation_id}
```

Command:

```powershell
wqb simu get 2UnwIe7g5jEcCgDvI4GpqO --max-wait-seconds 900
```

## `wqb simu create`

Create a simulation and wait for the final result. For multi-simulation, child simulations are also waited and included under top-level `children`. The initial `201 Created` is only `201 Created, waiting for results...`.

Raw API:

```text
POST /simulations
```

Command:

```powershell
wqb simu create --input api_inventory/examples/simulation_regular_close.json --max-wait-seconds 900
```
