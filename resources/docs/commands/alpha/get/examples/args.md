# Direct Argument Example

Real command:

```powershell
D:\_soft\Anaconda\envs\WQBRAIN\Scripts\wqb.exe alpha get YPNOpk3W --output "wqb_cli\\docs\\commands\alpha\get\outputs\alpha_get_output.json"
```

Real output:

```text
wqb_cli/docs/commands/alpha/get/outputs/alpha_get_output.json
```

Observed result:

```json
{
  "id": "YPNOpk3W",
  "type": "REGULAR",
  "is": {
    "turnover": 0.5664,
    "returns": 0.2343,
    "margin": 0.000828,
    "sharpe": 2.72,
    "fitness": 1.75
  }
}
```

