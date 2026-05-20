# File Output Example

Real command:

```powershell
D:\_soft\Anaconda\envs\WQBRAIN\Scripts\wqb.exe community export --source "wqb_cli\local\community\WQPCommunityState_20260505_141911.json" --output "wqb_cli\docs\commands\community\export\outputs\export_output.json"
```

Source file:

```text
wqb_cli/local/community/WQPCommunityState_20260505_141911.json
```

Output file:

```text
wqb_cli/docs/commands/community/export/outputs/export_output.json
```

The generated SQLite file is written to `wqb_cli/local/community/community.sqlite3` by default.
It is ignored by Git because it is large local data.
