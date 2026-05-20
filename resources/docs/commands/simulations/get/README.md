# simulations get

Fetch simulation status and final alpha id.

Command:

```powershell
wqb sim get <simulation_id> --output <output.json>
```

Default wait limit is 15 minutes:

```powershell
wqb sim get <simulation_id> --max-wait-seconds 900 --output <output.json>
```

Use `--max-wait-seconds` to override the limit for special cases.

Completion criteria:

- `response.body.status = COMPLETE`
- `response.body.alpha` exists

The response also includes `response.wait_events` when polling happened.
Each wait event records:

- `retry_after`: raw platform header value;
- `sleep_seconds`: actual local sleep time;
- `progress`: progress value parsed from response body, if present;
- `multiplier`: wait multiplier applied by the CLI.

If total waiting would exceed `max_wait_seconds`, the CLI stops polling and returns the latest response with:

- `response.wait_timed_out = true`
- `response.max_wait_seconds = 900.0` by default
