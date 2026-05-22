# alpha submit

Submit an alpha request and wait for `/alphas/{alpha_id}/submit` to finish, similar to simulation polling.

## Usage

```powershell
wqb alpha submit <alpha_id> --max-wait-seconds 1800 --output submit_result.json
```

## Behavior

- Runs `POST /alphas/{alpha_id}/submit` first.
- If POST is accepted, records `post_classification.reason=submit_api_accepted` and polls `GET /alphas/{alpha_id}/submit`.
- If GET returns `Retry-After`, sleeps `Retry-After * --retry-after-multiplier`; the default multiplier is `2`.
- If GET returns `429`, sleeps 60 seconds and retries.
- If `--max-wait-seconds` is exceeded, returns `submit_code=408` instead of treating the initial POST as final success.
- CLI output keeps full response bodies and full checks; it does not trim result fields for display.

## API accepted vs final submitted

`POST /alphas/{alpha_id}/submit` returning a 2xx/3xx status only means the platform accepted the submit request. It is not final submission success.

Final submission success is determined by the waited result: top-level `ok=true` and `classification.submit_code=200`. Any other final code means the submit request was accepted but the alpha was not finally submitted, or the request failed before it could enter the wait flow.

## Codes

- `200`: final submit completed, or platform reports the alpha is already submitted.
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
- `post_classification`: initial POST classification. `reason=submit_api_accepted` means API accepted the request, not final submission success.
