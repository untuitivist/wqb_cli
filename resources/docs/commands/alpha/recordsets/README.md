# alpha recordsets

List and fetch alpha recordsets.

List command:

```powershell
wqb alpha recordsets <alpha_id> --max-wait-seconds 900 --output <output.json>
```

Recordset commands follow `Retry-After` by default and return only when the result is ready, the request fails, or `--max-wait-seconds` is reached.

Fetch command:

```powershell
wqb alpha recordset <alpha_id> <record_set_name> --output <output.json>
```

Generic API equivalent:

```powershell
wqb api call GET "/alphas/{alpha_id}/recordsets/{record_set_name}" --input <input.json> --output <output.json>
```
