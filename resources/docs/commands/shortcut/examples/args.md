# Argument Examples

Authentication status:

```powershell
D:\_soft\Anaconda\envs\WQBRAIN\Scripts\wqb.exe shortcut whoami
```

Create and wait for a simulation:

```powershell
D:\_soft\Anaconda\envs\WQBRAIN\Scripts\wqb.exe shortcut simulate --input wqb_cli\docs\commands\simulations\create\fixtures\regular_fastexpr_single.json --output wqb_cli\docs\commands\shortcut\outputs\simulate_output.json
```

Alpha report:

```powershell
D:\_soft\Anaconda\envs\WQBRAIN\Scripts\wqb.exe shortcut alpha-report rKbwexz3 --output wqb_cli\docs\commands\shortcut\outputs\alpha_report_output.json
```

Data fields:

```powershell
D:\_soft\Anaconda\envs\WQBRAIN\Scripts\wqb.exe quick data-fields --region USA --delay 1 --universe TOP3000 --search volume --limit 5
```
