# Args Example

Command used for the real verification run:

```powershell
wqb alpha submit P0nLm7Zp --execute --max-wait-seconds 1800 --retry-after-multiplier 2 --output submit_wait_1800_P0nLm7Zp.json
```

Observed result:

- Initial POST was accepted through redirect/submit flow.
- The CLI polled `GET /alphas/P0nLm7Zp/submit` 56 times.
- Final result was `submit_code=403`.
- `classification.checks.PROD_CORRELATION.result` was `FAIL`.
- The alpha remained `UNSUBMITTED`.

This is the important behavior: the CLI did not treat the initial accepted POST as a successful final submission.
