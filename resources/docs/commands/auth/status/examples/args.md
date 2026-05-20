# Direct Argument Example

Real command:

```powershell
D:\_soft\Anaconda\envs\WQBRAIN\Scripts\wqb.exe auth status
```

Real output:

```text
wqb_cli/docs/commands/auth/status/outputs/status_output.json
```

Observed result:

```json
{
  "ok": true,
  "endpoint": "/authentication",
  "response": {
    "status_code": 200,
    "body": {
      "user": {
        "id": "JL40454"
      }
    }
  }
}
```

