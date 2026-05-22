# File IO Example

Real command:

```powershell
D:\_soft\Anaconda\envs\WQBRAIN\Scripts\wqb.exe sim create --input "wqb_cli\\docs\\commands\simulations\create\fixtures\simulation_create_input.json" --output "wqb_cli\\docs\\commands\simulations\create\outputs\simulation_create_output.json"
```

Real input:

```text
wqb_cli/docs/commands/simulations/create/fixtures/simulation_create_input.json
```

Real output:

```text
wqb_cli/docs/commands/simulations/create/outputs/simulation_create_output.json
```

Observed result shape:

```json
{
  "create_classification": {
    "status_code": 201,
    "reason": "simulation_created_waiting_for_results",
    "message": "201 Created, waiting for results..."
  },
  "classification": {
    "ok": true,
    "status": "COMPLETE",
    "reason": "simulation_finished"
  }
}
```

The output keeps the initial `201 Created` under `create`, but the command does not stop there. It waits up to `--max-wait-seconds` and reports final success or failure under `classification`.
