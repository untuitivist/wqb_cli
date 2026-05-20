# alpha submit

Submit an alpha and wait for `/alphas/{alpha_id}/submit` to finish, similar to simulation polling.

## Usage

```powershell
wqb alpha submit <alpha_id> --execute --max-wait-seconds 1800 --output submit_result.json
```

## Behavior

- Runs `POST /alphas/{alpha_id}/submit` first.
- If POST is accepted, polls `GET /alphas/{alpha_id}/submit`.
- If GET returns `Retry-After`, sleeps `Retry-After * --retry-after-multiplier`; the default multiplier is `2`.
- If GET returns `429`, sleeps 60 seconds and retries.
- If `--max-wait-seconds` is exceeded, returns `submit_code=408` instead of treating the initial POST as final success.
- CLI output keeps full response bodies and full checks; it does not trim result fields for display.

## Codes

- `200`: submit completed or platform reports already submitted.
- `408`: submit wait timed out.
- `460`: regular/super submission quota or submission rule failed.
- `461`: Power Pool monthly submission failed.
- `462`: Power Pool submission failed.
- `401`: unauthorized.
- `403`: other submit forbidden result.
- `429`: rate limited.

## Output

- `post`: initial POST result.
- `wait`: final GET `/submit` result plus all `wait_events`.
- `alpha`: `GET /alphas/{alpha_id}` after wait ends.
- `classification`: final submit classification.
- `post_classification`: initial POST classification.
