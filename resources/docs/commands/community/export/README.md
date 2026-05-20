# community export

Import a WebDataScope community export file into local SQLite.

Supported source formats:

- `WQPCommunityState_*.json`
- `WQPCommunityState_*.wqcs`

Command:

```powershell
wqb community export --source <WQPCommunityState.json> --sqlite <community.sqlite3> --output <output.json>
```

If `--source` is omitted, the command uses the newest export file found in configured local export locations.
The CLI checks `wqb_cli/local/community/`, then common download or WebDataScope export locations.

If `--sqlite` is omitted, the command writes to:

```text
wqb_cli/local/community/community.sqlite3
```

Do not write the generated SQLite into command docs. Community SQLite files are large and should be treated as local data.
