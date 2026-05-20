# File IO Example

`sim get` does not need a body input.
The real example uses the simulation created by `simulations/create`:

```powershell
D:\_soft\Anaconda\envs\WQBRAIN\Scripts\wqb.exe sim get 25hy8yeL94KI9BQwSfxUVXE --max-wait-seconds 900 --output "wqb_cli\\docs\\commands\simulations\get\outputs\simulation_get_latest_output.json"
```

Real output:

```text
wqb_cli/docs/commands/simulations/get/outputs/simulation_get_latest_output.json
```

Observed result:

```json
{
  "id": "25hy8yeL94KI9BQwSfxUVXE",
  "status": "ERROR",
  "message": "There was an error while running the simulation. Please try again or contact BRAIN support if this problem persists.",
  "wait_timed_out": false,
  "max_wait_seconds": 900.0
}
```

Additional real completed output:

```text
wqb_cli/docs/commands/simulations/get/outputs/simulation_get_created_output.json
```

Observed result:

```json
{
  "id": "4kxZwJbUM4Xy9Gz8Co6vjyn",
  "elapsed_ms": 169697,
  "retries": 32,
  "status": "COMPLETE",
  "alpha": "LLnw1Yqv"
}
```
