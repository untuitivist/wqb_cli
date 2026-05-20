# Direct Argument Example

Real command:

```powershell
D:\_soft\Anaconda\envs\WQBRAIN\Scripts\wqb.exe sim options --output "wqb_cli\\docs\\commands\simulations\options\outputs\options_command_output.json"
```

Real output:

```text
wqb_cli/docs/commands/simulations/options/outputs/options_command_output.json
```

Observed result:

```json
{
  "CHN_universe": ["TOP2000U"],
  "decay": {
    "minValue": 0,
    "maxValue": 512
  },
  "language": ["PYTHON", "FASTEXPR"]
}
```

