# Notes

Waiting can take much longer than 60 seconds, but the default CLI cap is 15 minutes.
The real IO example took `169697 ms` and `32` retries.

The CLI should follow `Retry-After` until completion.
It stops before exceeding `--max-wait-seconds`, default `900`.
When progress is stuck around `0.15` or `0.35`, polling too frequently is noisy and not useful.
The CLI now multiplies the platform `Retry-After` by `10` when parsed progress is within these sticky bands:

- `abs(progress - 0.15) <= 0.01`
- `abs(progress - 0.35) <= 0.01`

The final output records this in `response.wait_events`.
If the wait cap is hit, the output records `response.wait_timed_out = true`.

Possible non-actionable platform failures:

```json
{"status": "FAIL"}
```

```json
{"status": "ERROR", "message": "There was an error while running the simulation. Please try again or contact BRAIN support if this problem persists."}
```

Real long-wait example:

- simulation id: `25hy8yeL94KI9BQwSfxUVXE`
- first local wait exceeded the old local command timeout behavior
- later `sim get` returned platform generic `ERROR`
- output file: `outputs/simulation_get_latest_output.json`
