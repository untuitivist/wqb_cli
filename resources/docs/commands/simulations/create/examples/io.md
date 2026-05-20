# File IO Example

Real command:

```powershell
D:\_soft\Anaconda\envs\WQBRAIN\Scripts\wqb.exe sim create --input "wqb_cli\\docs\\commands\simulations\create\fixtures\simulation_create_input.json" --execute --output "wqb_cli\\docs\\commands\simulations\create\outputs\simulation_create_output.json"
```

Real input:

```text
wqb_cli/docs/commands/simulations/create/fixtures/simulation_create_input.json
```

Real output:

```text
wqb_cli/docs/commands/simulations/create/outputs/simulation_create_output.json
```

Observed result:

```json
{
  "status_code": 201,
  "location": "https://api.worldquantbrain.com/simulations/25hy8yeL94KI9BQwSfxUVXE",
  "retry_after": "5.0"
}
```
