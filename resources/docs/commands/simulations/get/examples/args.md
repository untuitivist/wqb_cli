# Direct Argument Example

Real command:

```powershell
D:\_soft\Anaconda\envs\WQBRAIN\Scripts\wqb.exe sim get 2nFEcbbu55rausiX9XkI2d --output "wqb_cli\\docs\\commands\simulations\get\outputs\simulation_get_existing_output.json"
```

Equivalent explicit 15-minute cap:

```powershell
D:\_soft\Anaconda\envs\WQBRAIN\Scripts\wqb.exe sim get 2nFEcbbu55rausiX9XkI2d --max-wait-seconds 900 --output "wqb_cli\\docs\\commands\simulations\get\outputs\simulation_get_existing_output.json"
```

Real output:

```text
wqb_cli/docs/commands/simulations/get/outputs/simulation_get_existing_output.json
```

Observed result:

```json
{
  "id": "2nFEcbbu55rausiX9XkI2d",
  "status": "COMPLETE",
  "alpha": "YPNOpk3W",
  "wait_timed_out": false,
  "max_wait_seconds": 900.0
}
```
