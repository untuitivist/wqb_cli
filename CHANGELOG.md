# Changelog

All notable changes are grouped by the package versions evidenced in `pyproject.toml` and the GitHub release history.

## 0.6.1 - 2026-09-22

### Fixed

- Retry confirmed simulation failures once by default, then record and skip exhausted experiments. Confirmed retries are no longer blocked by the pending-simulation resend interval.
- Distinguish daily simulation quota from concurrency/rate limits and authentication. A confirmed daily limit persists a pause until the next America/New_York midnight, with daylight-saving handling, while accepted results continue collecting.
- Use the authenticated forum page's shared CSRF token for community writes and image registration. The Help Center session token previously caused live uploads to fail with HTTP 401.

### Added

- `community create/update --html` with local-image upload, durable SHA-256 asset receipts, exact prepared-body output and post-publication readback.
- `community image-upload` and the two official user-image endpoints in the raw community API inventory. HTML dry runs validate files entirely offline; uncertain writes remain non-replaying.
- Replace the existing v0.6.1 release assets with this correction, retaining the same version.

### Changed

- Standardize the simulation command as `wqb simu`. The former `wqb sim` name is no longer accepted; migrate scripts by replacing that command token with `simu`.
- Rename the command module, parser, handler, argument destination, tests and generated documentation to match `simu`.
- Update command examples and workflows. Compatible FASTEXPR Regular batches, including GLB, contain up to 10 candidates and continue dispatching without awaiting prior results. HTTP 429 respects Retry-After with a 10-second fallback.
- SQLite schema 8 retains confirmed failure attempts and migrates historical retry records. `--max-simulation-retries` controls the persistent budget independently of request throttling and enrichment retries. ALL, Super and Python keep single-object scheduling.

## 0.6.0 - 2026-09-22

### Added

- Online `community` commands for forum sections, posts, comments, search, author activity and an independent API inventory/raw layer.
- `sqlitecom sync` with cursor pagination, resumable pending work, update-time overlap, comment retrieval, writer coordination and transactional SQLite/FTS updates.
- Offline author/date search, full post reading, schema inspection and parameterized read-only SQL with row limits and execution deadlines.
- Forum SSO renewal and CSRF for explicit writes, reusing existing BRAIN authentication. Transient reads retry within a budget; writes are never automatically replayed.

### Changed

- Local `community search/stats/export` moved to `sqlitecom search/stats/import`. `community search` now queries the live forum.
- Plugin imports merge records, retain omitted documentation and preserve newer synchronized posts. Existing Regular/ALL/Super simulation interfaces remain unchanged.

## 0.5.0 - 2026-09-22

### Added

- Native REGION_AGNOSTIC/ALL support in `sim` (alias `simu`), raw simulation requests and `sqlitesimu`, with single-parent requests, regional child details/PnL and resumable schema-v7 storage.
- `api call --dry-run`, `sim create --dry-run` and `sqlitesimu --no-resend` runtime options. Regular and ALL can share one durable run while ALL is always sent as an individual HTTP object.
- Refreshed 131 API paths against current platform references and read-only probes, growing the catalog from 109 to 127 paths. Added schema shapes, explicit advertised-method evidence, per-endpoint docs and a refresh report without private option choices.
- User commands for named activity history, Osmosis summary and scaling status, activity streaks, tags and submission activity.
- `wqb --version` reports the installed runtime version for deployment verification.

### Fixed

- Normal Osmosis scaling-status HTTP 204 responses no longer trigger authentication replay when the endpoint contract declares them successful.
- Enrichment honors successful HTTP responses with Retry-After before parsing results; RA parents never request or fabricate parent PnL. Unknown POST outcomes remain isolated.

### Changed

- Split BatchSimu template discovery density from positive-direction validation and final eligibility. `template-report` can now consume the pre-registered F analysis contract, report absolute-metric forward/reverse signals with Wilson intervals, and require a new simulation for every reverse-direction discovery.
- Distinguished simulation-capacity, cancellation-limit, and API-rate-limit `429` responses from authentication failures. CoreClient and `sqlitesimu` now preserve server backpressure without clearing cookies or replaying mutating requests, while `204`, `401`, and authentication-like `429` responses retain the existing aggressive reauthentication behavior.
- Made parent-simulation requeue restore missing durable simulation-queue entries atomically, including operational recovery after a remotely deleted parent was first observed as `404`.

## 0.4.0 - 2026-08-18

### Added

- Added a command-plugin SDK and the built-in `sqlitesimu` plugin with `init`, `enqueue`, `run`, `resume`, `status`, `cancel`, and `export` commands for durable batch simulations.
- Added SQLite-backed run leases, resumable simulation and enrichment queues, normalized Alpha/PnL persistence, auditable state/event history, and the legacy-compatible `simued_alpha_is_pnl` view.
- Added strict template-family manifest validation with lineage and identity hashes, plus terminal template reports covering per-family performance, checks, representative Alphas, and READY coverage.
- Added two physically isolated A-M workflow document sets: bounded adaptive simulation research and agent-independent template-family batch research with slow final checks and explicit Alpha submission gates.

### Changed

- Added one-shot API calls so workflow runtimes persist `Retry-After` scheduling instead of sleeping inside the HTTP client.
- Reworked authentication recovery to match `WQBSession` behavior for `204`, `401`, and `429`, with bounded global replay, stale-cookie cleanup, concurrent-login coordination, and five additional `sqlitesimu` login attempts.
- Replaced client-side simulation slot limits with server `429 / Retry-After` backpressure, while prioritizing due simulation and enrichment polling so large queues cannot starve active work.
- Preserved ambiguous simulation POST outcomes as `SIMULATE_UNKNOWN` instead of blindly replaying mutating requests; cancellation now consumes operational queues without deleting candidate, batch, Alpha, PnL, or event history.
- Standardized terminology: simulate refers to creating a backtest, while submit refers only to the final `wqb alpha submit` action.

## 0.3.2 - 2026-07-16

### Added

- Added generic competition and consultant leaderboard scopes, competition Guidelines/FAQ helpers, and SPC prompt-submission commands for `GET`, `POST`, `PUT`, and `PATCH`.
- Added canonical inventory entries, endpoint examples, raw-call documentation, CLI coverage reports, and tests for the new competition resources.
- Added Basic Auth retry support when alpha endpoints reject an otherwise valid cookie session with `401`.

### Changed

- Expanded the bundled complete API inventory from 104 endpoints and 126 method cases to 109 endpoints and 134 method cases without removing existing registrations.
- Strengthened workflow-node runtime constraints and CLI usage guidance.
- Synchronized the runtime `wqb_cli.__version__` value with package metadata; it had remained at the stale, unpublished value `0.1.0`.
- Added bilingual per-version Added/Changed/Removed records to the README files.

### Removed

- Removed obsolete analyst/PV vector sample JSON files and a redundant workflow document; no published CLI command or registered API endpoint was removed.

## 0.3.1 - 2026-05-22

### Added

- Added the `wqb` console entry point, package-local runtime defaults, keyring-backed authentication, local configuration, community search, scope inspection, shortcut commands, and CLI smoke tests.
- Added the bundled API inventory, generated command documentation, alpha submit polling, and full non-JSON response capture.
- Added comprehensive English and Simplified Chinese README documentation and project branding.

### Changed

- Reworked the project into the agent-first `wqb_cli` package layout and updated package metadata, repository links, workflow guidance, and release documentation.
- Replaced MIT licensing with GPL-3.0-only plus the Commons Clause license condition.

### Removed

- Removed the legacy `wqb_core` package-discovery/test layout and unused legacy resources during the package restructure.

## 0.2.5 - 2026-05-13

### Added

- Added the initial packaged WorldQuant BRAIN API wrapper and agent-oriented workflow baseline with `requests`, `pandas`, and `msgpack` dependencies.

### Changed

- None; this was the initial package-metadata baseline.

### Removed

- None.
