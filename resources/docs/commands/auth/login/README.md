# auth login

Authenticate against BRAIN and persist cookies for later CLI calls.

Command:

```powershell
wqb api call POST /authentication --env-auth --input <input.json> --output <output.json>
```

Use `--env-auth` so credentials are read from `wqb_cli/local/.env`.
The input file should contain only non-secret request fields such as `expiry`.

Input schema used in examples:

```json
{
  "json": {
    "expiry": 3600
  }
}
```

Success criteria:

- `response.status_code = 201`
- `response.body.user.id` exists
- `response.body.token.expiry > 0`
