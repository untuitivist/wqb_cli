# Backtest Mode Examples

`wqb sim create` uses the same `/simulations` API for the common backtest modes:

- `REGULAR` + `FASTEXPR` single simulation.
- `REGULAR` + `FASTEXPR` multi-simulation.
- `REGULAR` + `PYTHON` single simulation.
- `SUPER` single simulation.

The command now waits by default. The initial `201 Created` is only an intermediate API-accepted state, reported as `201 Created, waiting for results...`. Final success or failure is determined by the waited `classification`.

Input JSON examples are in `examples/input_json.md`.

## Concurrency And Batching

Distinguish the number of expressions inside one request from the number of simulation requests started by an external scheduler:

- `REGULAR_FASTEXPR_MULTI`: one multi request supports up to 10 expressions.
- Recommended `REGULAR_FASTEXPR_MULTI` batch size: 10 outside `GLB`, 5 for `GLB`.
- `REGULAR_PYTHON`: no multi-simulation; one simulation per request.
- `SUPER`: no REGULAR-style multi batch; one SUPER simulation per request.
- External REGULAR concurrency: max 8 when `region != "GLB"`, max 4 when `region == "GLB"`.
- External SUPER concurrency: max 3.

Recommended scheduler logic:

```text
if type == SUPER:
    concurrent_requests = 3
    batch_size = 1
elif language == PYTHON:
    concurrent_requests = 8 if region != "GLB" else 4
    batch_size = 1
elif language == FASTEXPR:
    concurrent_requests = 8 if region != "GLB" else 4
    batch_size = 10 if region != "GLB" else 5
```

`batch_size` only applies to `REGULAR_FASTEXPR_MULTI`. `concurrent_requests` belongs to the external scheduler; it is not a `wqb sim create` argument.

## REGULAR FASTEXPR Single

Input file:

```text
wqb_cli/docs/commands/simulations/create/fixtures/regular_fastexpr_single.json
```

Input JSON: `examples/input_json.md#regular-fastexpr-single-simulation`.

Command:

```powershell
D:\_soft\Anaconda\envs\WQBRAIN\Scripts\wqb.exe sim create --input "wqb_cli\\docs\\commands\simulations\create\fixtures\regular_fastexpr_single.json" --max-wait-seconds 900 --output "wqb_cli\\docs\\commands\simulations\create\outputs\regular_fastexpr_single_create.json"
```

Final observed result:

```json
{
  "simulation_id": "1sA5Evcma4GlbBexARpKkiX",
  "type": "REGULAR",
  "language": "FASTEXPR",
  "status": "WARNING",
  "alpha": "rKbwexz3",
  "warning": "REVERSION_COMPONENT"
}
```

## REGULAR FASTEXPR Multi

Input file:

```text
wqb_cli/docs/commands/simulations/create/fixtures/regular_fastexpr_multi.json
```

Input JSON: `examples/input_json.md#regular-fastexpr-multi-simulation`.

Command:

```powershell
D:\_soft\Anaconda\envs\WQBRAIN\Scripts\wqb.exe sim create --input "wqb_cli\\docs\\commands\simulations\create\fixtures\regular_fastexpr_multi.json" --max-wait-seconds 900 --output "wqb_cli\\docs\\commands\simulations\create\outputs\regular_fastexpr_multi_create.json"
```

Multi-simulation constraints:

- The input file is a JSON array.
- Items in one multi request must share exactly these settings: `delay`, `region`, `instrumentType`, `language`.
- The parent result contains child ids, and `sim create` waits for those child simulations too.
- Child simulations contain each expression's final alpha/result.

Parent summary:

```json
{
  "simulation_id": "9Xb69y251KaGqyWKGddux",
  "status": "COMPLETE",
  "children": [
    "2gwGaU59a5dqcySQM4Ft1gn",
    "3RTDPvcRM4JtczS18UmrIqML"
  ]
}
```

If you need to re-check a child later, use `sim get` directly:

```powershell
D:\_soft\Anaconda\envs\WQBRAIN\Scripts\wqb.exe sim get 2gwGaU59a5dqcySQM4Ft1gn --max-wait-seconds 900 --output "wqb_cli\\docs\\commands\simulations\get\outputs\regular_fastexpr_multi_child_1_get.json"
D:\_soft\Anaconda\envs\WQBRAIN\Scripts\wqb.exe sim get 3RTDPvcRM4JtczS18UmrIqML --max-wait-seconds 900 --output "wqb_cli\\docs\\commands\simulations\get\outputs\regular_fastexpr_multi_child_2_get.json"
```

## REGULAR PYTHON Single

Input file:

```text
wqb_cli/docs/commands/simulations/create/fixtures/regular_python_single.json
```

Input JSON: `examples/input_json.md#regular-python-single-simulation`.

Command:

```powershell
D:\_soft\Anaconda\envs\WQBRAIN\Scripts\wqb.exe sim create --input "wqb_cli\\docs\\commands\simulations\create\fixtures\regular_python_single.json" --max-wait-seconds 900 --output "wqb_cli\\docs\\commands\simulations\create\outputs\regular_python_single_create.json"
```

Final observed result:

```json
{
  "simulation_id": "2iKEQ32Xm4QFcHqoGYebfM",
  "type": "REGULAR",
  "language": "PYTHON",
  "status": "COMPLETE",
  "alpha": "e7nPQPpl"
}
```

## SUPER Single

Input file:

```text
wqb_cli/docs/commands/simulations/create/fixtures/super_single.json
```

Input JSON: `examples/input_json.md#super-single-simulation`.

Command:

```powershell
D:\_soft\Anaconda\envs\WQBRAIN\Scripts\wqb.exe sim create --input "wqb_cli\\docs\\commands\simulations\create\fixtures\super_single.json" --max-wait-seconds 900 --output "wqb_cli\\docs\\commands\simulations\create\outputs\super_single_create.json"
```

Final observed result:

```json
{
  "simulation_id": "41NcougeE57e8Ay3rfZderr",
  "type": "SUPER",
  "status": "COMPLETE",
  "alpha": "pwnkdErb",
  "selection": "own == 1",
  "combo": "1"
}
```

## Alpha Details

After a simulation returns an alpha, inspect it with `alpha get`:

```powershell
D:\_soft\Anaconda\envs\WQBRAIN\Scripts\wqb.exe alpha get rKbwexz3 --output "wqb_cli\\docs\\commands\alpha\get\outputs\regular_fastexpr_single_alpha.json"
```

Alpha detail output verifies the alpha id, language, status, and metric fields. It is not a submission-readiness decision by itself.
