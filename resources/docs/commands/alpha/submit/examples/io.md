# File IO Example

Command:

```powershell
wqb alpha submit P0nLm7Zp --execute --max-wait-seconds 1800 --retry-after-multiplier 2 --output outputs/submit_wait_P0nLm7Zp_full_output.json
```

Output file:

```text
resources/docs/commands/alpha/submit/outputs/submit_wait_P0nLm7Zp_full_output.json
```

The output file is a full real CLI output captured from the platform. It intentionally keeps the full `classification.checks`, `wait.wait_events`, `post`, `wait`, and `alpha` sections.
