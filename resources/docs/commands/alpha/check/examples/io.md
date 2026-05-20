# File IO Example

Real command:

```powershell
D:\_soft\Anaconda\envs\WQBRAIN\Scripts\wqb.exe api call GET "/alphas/{alpha_id}/check" --input "wqb_cli\\docs\\commands\alpha\check\fixtures\alpha_check_input.json" --output "wqb_cli\\docs\\commands\alpha\check\outputs\alpha_check_retry_after_output.json"
```

Retry command:

```powershell
D:\_soft\Anaconda\envs\WQBRAIN\Scripts\wqb.exe api call GET "/alphas/{alpha_id}/check" --input "wqb_cli\\docs\\commands\alpha\check\fixtures\alpha_check_input.json" --output "wqb_cli\\docs\\commands\alpha\check\outputs\alpha_check_output.json"
```

Real input:

```text
wqb_cli/docs/commands/alpha/check/fixtures/alpha_check_input.json
```

Real outputs:

```text
wqb_cli/docs/commands/alpha/check/outputs/alpha_check_retry_after_output.json
wqb_cli/docs/commands/alpha/check/outputs/alpha_check_output.json
```

