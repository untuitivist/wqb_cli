# Durable Regular, Super and ALL simulations

`wqb sqlitesimu run manifest.json --db simulations.sqlite3 --no-resend --output result.json`

The command blocks until a terminal run state. `resume RUN_ID` continues the same database, including previously accepted remote work and partially collected results. `--no-resend` disables repeated POSTs while an accepted simulation is pending. Explicit rejected requests can still retry after backpressure. Ambiguous POST outcomes remain `SIMULATE_UNKNOWN` and are never automatically repeated.

A manifest may mix REGULAR and REGION_AGNOSTIC candidates. ALL uses `type: REGION_AGNOSTIC`, `settings.region: ALL`, delay 1, universe LARGE/MEDIUM/SMALL, and a `regular` expression. Each ALL request is one object; the server does not accept ALL in a batch array. The same sender interleaves ALL with compatible Regular batches and honors shared server backpressure.

ALL simulation completion identifies an RA_PARENT Alpha. Its `children` are Alpha IDs, not child simulation IDs. The worker fetches every regional RA_CHILD detail and PnL before marking that parent experiment READY. A parent has no independent PnL. HTTP 200 with Retry-After means enrichment is still pending and does not consume the failure budget.

Schema 7 preserves existing experiments and the earlier extension's `region_agnostic_children` and `region_agnostic_child_pnl` tables. Export retains one experiment/result per parent and adds `region_agnostic_children`, containing child detail, checks, raw PnL response and normalized PnL. The existing regular `pnl_paths` excludes RA parents. Analyze RA quality and correlations by region; do not treat child count as new independent experiments or missing parent Sharpe as a failed regional signal.

`sim`, `simu` and `sqlitesimu` perform backtests. Formal Alpha submission remains a separate command.
