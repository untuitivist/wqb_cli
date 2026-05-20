# `/competition-levels/{competition_level_id}/icon`

- URL template: `https://api.worldquantbrain.com/competition-levels/{competition_level_id}/icon`
- Methods: `GET`
- Sources: `platform_dynamic_capture`
- Safe probe: `True`
- Description: Observed by passive platform network capture.

## Probe

- Skipped/Error: `Observed by platform dynamic network capture; no separate safe probe was run.`

## Dynamic Capture

### `GET /competition-levels/none/icon`

- Seen count: `1`
- Status codes: `200`
- Query keys: ``
- Content types: `image/svg+xml`

## Endpoint Tests

### `GET /competition-levels/{competition_level_id}/icon`

- Status: `tested`
- Tested path: `/competition-levels/none/icon`
- HTTP: `200 OK`
- Elapsed: `284 ms`
- Content-Type: `image/svg+xml`
- Allow: `GET, HEAD, OPTIONS`
