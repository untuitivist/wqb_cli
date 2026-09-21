# Durable Regular, Super and ALL simulations

`wqb sqlitesimu run manifest.json --db simulations.sqlite3 --no-resend --output result.json`

The command blocks until a terminal run state. `resume RUN_ID` continues the same database, including previously accepted remote work and partially collected results. `--no-resend` disables repeated POSTs while an accepted simulation is pending. Explicit rejected requests can still retry after backpressure. Ambiguous POST outcomes remain `SIMULATE_UNKNOWN` and are never automatically repeated.

A manifest may mix REGULAR and REGION_AGNOSTIC candidates. ALL uses `type: REGION_AGNOSTIC`, `settings.region: ALL`, delay 1, universe LARGE/MEDIUM/SMALL, and a `regular` expression. Each ALL request is one object; the server does not accept ALL in a batch array. The same sender interleaves ALL with compatible Regular batches and honors shared server backpressure.

Compatible FASTEXPR Regular candidates, including GLB, are sent in groups of up to 10. The sender saves each accepted Location and immediately continues with the next batch without waiting for its results. There is no client simulation slot cap. HTTP 429 defers the request using Retry-After, falling back to 10 seconds; it does not count as a simulation failure. Super, ALL and Python requests retain their single-object scheduling. Partial final batches are also sent.

`--max-simulation-retries 1` is the default: a confirmed ERROR, FAIL or CANCELLED result retries once, then becomes PERMANENT_FAILURE so other experiments can continue. `--retry-seconds` controls that delay independently of `--resend-seconds` and `--no-resend`. Schema 8 stores each confirmed failed attempt in `simulation_failures`, including its error and raw response, and preserves the budget across restarts. Exported experiments include the failure count and last error. Read failures of accepted remote progress continue to retry without reposting it; ambiguous POSTs still require reconciliation.

The run finishes as COMPLETED_WITH_ERRORS (exit code 3) if permanent failures remain. A multi-stage caller should archive those failures and continue its next stage when that outcome is acceptable. `--max-attempts` separately limits enrichment failures.

HTTP 429 with `DAILY_SIMULATION_LIMIT_EXCEEDED` (or the explicit daily-limit message) pauses the sender until the next midnight in `America/New_York`, including daylight-saving changes. That deadline persists in SQLite, applies to all runs in the database, and appears in `status` as `daily_limit_not_before` (Unix seconds). Restarting the worker or receiving an ordinary short rate limit cannot shorten it. Accepted result and PnL collection continues while new simulations wait. The API response determines exhaustion; local experiment counts cannot account for other clients or platform counting rules. An ordinary concurrent-simulation limit does not trigger an overnight pause.

ALL simulation completion identifies an RA_PARENT Alpha. Its `children` are Alpha IDs, not child simulation IDs. The worker fetches every regional RA_CHILD detail and PnL before marking that parent experiment READY. A parent has no independent PnL. HTTP 200 with Retry-After means enrichment is still pending and does not consume the failure budget.

Schema 8 preserves existing experiments and the earlier extension's `region_agnostic_children` and `region_agnostic_child_pnl` tables. Export retains one experiment/result per parent and adds `region_agnostic_children`, containing child detail, checks, raw PnL response and normalized PnL. The existing regular `pnl_paths` excludes RA parents. Analyze RA quality and correlations by region; do not treat child count as new independent experiments or missing parent Sharpe as a failed regional signal.

`simu` and `sqlitesimu` perform backtests. Formal Alpha submission remains a separate command.
