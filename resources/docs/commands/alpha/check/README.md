# alpha check

Run or fetch platform checks for an alpha.

Command:

```powershell
wqb alpha check <alpha_id> --max-wait-seconds 900 --output <output.json>
```

`alpha check` follows `Retry-After` by default and returns only when the check body is ready, the request fails, or the wait reaches `--max-wait-seconds`.

Generic API equivalent:

```powershell
wqb api call GET "/alphas/{alpha_id}/check" --input <input.json> --output <output.json>
```

Important checks include:

- `LOW_SHARPE`
- `LOW_FITNESS`
- `LOW_TURNOVER`
- `HIGH_TURNOVER`
- `SELF_CORRELATION`
- `DATA_DIVERSITY`
- `PROD_CORRELATION`
- `REGULAR_SUBMISSION`
- `LOW_2Y_SHARPE`
- `MATCHES_PYRAMID`
