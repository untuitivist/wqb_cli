# File Output Example

Real command:

```powershell
D:\_soft\Anaconda\envs\WQBRAIN\Scripts\wqb.exe community stats --output "wqb_cli\docs\commands\community\stats\outputs\stats_output.json"
```

Output file:

```text
wqb_cli/docs/commands/community/stats/outputs/stats_output.json
```

This command has no JSON input file because it only reads the configured SQLite database.
The persisted JSON output is the same object printed to stdout.

