# Changelog

## Unreleased

- Added package-local runtime defaults under `wqb_cli/local/`.
- Added local community database commands: `wqb community export/search/stats`.
- Added shortcut layer: `wqb shortcut` and `wqb quick`.
- Added local config commands: `wqb config init/list/get/set/set-secret`.
- Added keyring-backed credential storage with `.env` fallback.
- Added CLI smoke tests and release check documentation.
- Added local `wqb scope` commands for `wqb_cli/local/data_all` quick-index and full-pickle inspection.
- Added submit polling for `wqb alpha submit`: POST is followed by GET `/alphas/{alpha_id}/submit` until completion, classified failure, or timeout.
- Changed CLI response capture to keep full non-JSON response bodies instead of truncating text output.
