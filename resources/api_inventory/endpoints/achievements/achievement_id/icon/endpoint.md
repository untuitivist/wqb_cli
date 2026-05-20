# `/achievements/{achievement_id}/icon`

- URL template: `https://api.worldquantbrain.com/achievements/{achievement_id}/icon`
- Methods: `GET`
- Sources: `platform_dynamic_capture`
- Safe probe: `True`
- Description: Observed by passive platform network capture.

## Probe

- Skipped/Error: `Observed by platform dynamic network capture; no separate safe probe was run.`

## Dynamic Capture

### `GET /achievements/ALPHA_PERF_EXCELLENT/icon`

- Seen count: `1`
- Status codes: `200`
- Query keys: ``
- Content types: `image/svg+xml`
### `GET /achievements/ALPHA_PERF_GOOD/icon`

- Seen count: `1`
- Status codes: `200`
- Query keys: ``
- Content types: `image/svg+xml`
### `GET /achievements/ALPHA_PERF_SPECTACULAR/icon`

- Seen count: `1`
- Status codes: `200`
- Query keys: ``
- Content types: `image/svg+xml`
### `GET /achievements/CONSULTANT_SUBMIT/icon`

- Seen count: `1`
- Status codes: `200`
- Query keys: ``
- Content types: `image/svg+xml`
### `GET /achievements/SIMULATION_100/icon`

- Seen count: `1`
- Status codes: `200`
- Query keys: ``
- Content types: `image/svg+xml`
### `GET /achievements/SIMULATION_20/icon`

- Seen count: `1`
- Status codes: `200`
- Query keys: ``
- Content types: `image/svg+xml`
### `GET /achievements/SUBMIT_1/icon`

- Seen count: `1`
- Status codes: `200`
- Query keys: ``
- Content types: `image/svg+xml`
### `GET /achievements/SUBMIT_10/icon`

- Seen count: `1`
- Status codes: `200`
- Query keys: ``
- Content types: `image/svg+xml`
### `GET /achievements/SUPER_ALPHA/icon`

- Seen count: `1`
- Status codes: `200`
- Query keys: ``
- Content types: `image/svg+xml`

## Endpoint Tests

### `GET /achievements/{achievement_id}/icon`

- Status: `tested`
- Tested path: `/achievements/ALPHA_PERF_EXCELLENT/icon`
- HTTP: `200 OK`
- Elapsed: `371 ms`
- Content-Type: `image/svg+xml`
- Allow: `GET, HEAD, OPTIONS`
