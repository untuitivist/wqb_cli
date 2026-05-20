# File IO Example

Real command:

```powershell
D:\_soft\Anaconda\envs\WQBRAIN\Scripts\wqb.exe api call POST /authentication --env-auth --input "wqb_cli\\docs\\commands\auth\login\fixtures\login_input.json" --execute --output "wqb_cli\\docs\\commands\auth\login\outputs\login_output.json"
```

Real input:

```text
wqb_cli/docs/commands/auth/login/fixtures/login_input.json
```

Real output:

```text
wqb_cli/docs/commands/auth/login/outputs/login_output.json
```

Observed result:

```json
{
  "ok": true,
  "endpoint": "/authentication",
  "response": {
    "status_code": 201,
    "body": {
      "user": {
        "id": "JL40454"
      },
      "token": {
        "expiry": 3600.0
      }
    }
  }
}
```

