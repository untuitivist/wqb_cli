# Stalled simulation recovery

`sqlitesimu run` and `resume` now default to:

- `--simulation-timeout-seconds 1800`: after platform acceptance, cancel unfinished parent or child simulations through `DELETE /simulations/{simulation_id}` at the next poll.
- `--max-not-found-retries 3`: the first HTTP 404 is followed by up to three retries. Four consecutive 404 responses trigger resimulation.
- `--max-simulation-retries 1`: at most one replacement attempt per experiment across failure, cancellation and missing-result recovery; exhausted experiments become permanent failures.

Queue waiting and daily-limit sleeping do not count toward remote execution time. Acceptance timestamps and consecutive missing responses persist in SQLite schema 9. Migration backfills active jobs from acceptance events; if no acceptance evidence exists, timing conservatively starts at the first new observation.

Completed results take precedence over timeout cancellation. Cancellation is confirmed by HTTP 204 or a 200 CANCELLED/CANCELED response. HTTP 202, transport errors and other ambiguous responses keep the original simulation in polling, honoring Retry-After; they never cause an immediate replacement. Already completed batch items are preserved by the existing per-experiment retry ownership checks.

For manual cancellation, use `wqb simu cancel SIMULATION_ID`. This cancels a simulation, not an Alpha or an entire durable run. A successful asynchronous cancellation response still requires follow-up polling.
