# auth status

Check whether the current CLI cookie session is valid.

Command:

```powershell
wqb auth status
```

Success criteria:

- `response.status_code = 200`
- `response.body.user.id` exists
- `response.body.token.expiry > 0`

