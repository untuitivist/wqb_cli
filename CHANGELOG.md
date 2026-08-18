# Changelog

All notable changes are grouped by the package versions evidenced in `pyproject.toml` and the GitHub release history.

## Unreleased

No unreleased changes yet.

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
