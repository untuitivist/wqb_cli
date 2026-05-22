# Direct Argument Example

Real command:

```powershell
D:\_soft\Anaconda\envs\WQBRAIN\Scripts\wqb.exe alpha check YPNOpk3W --max-wait-seconds 900 --output <output.json>
```

Real full-check output:

```text
wqb_cli/docs/commands/alpha/check/outputs/alpha_check_output.json
```

Observed full-check result:

```json
{
  "LOW_SHARPE": "PASS",
  "LOW_FITNESS": "PASS",
  "LOW_TURNOVER": "PASS",
  "HIGH_TURNOVER": "PASS",
  "SELF_CORRELATION": 0.1465,
  "PROD_CORRELATION": 0.6514,
  "LOW_2Y_SHARPE": 2.19
}
```
