# alpha recordsets

List and fetch alpha recordsets.

List command:

```powershell
wqb alpha recordsets <alpha_id> --output <output.json>
```

Fetch command:

```powershell
wqb alpha recordset <alpha_id> <record_set_name> --output <output.json>
```

Generic API equivalent:

```powershell
wqb api call GET "/alphas/{alpha_id}/recordsets/{record_set_name}" --input <input.json> --output <output.json>
```

