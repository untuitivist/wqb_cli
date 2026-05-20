# `/users/self/alphas/summary`

- URL template: `https://api.worldquantbrain.com/users/self/alphas/summary`
- Methods: `GET`
- Sources: `platform_dynamic_capture`
- Safe probe: `True`
- Description: Observed by passive platform network capture.

## Probe

- Skipped/Error: `Observed by platform dynamic network capture; no separate safe probe was run.`

## Dynamic Capture

### `GET /users/self/alphas/summary`

- Seen count: `1`
- Status codes: `200`
- Query keys: ``
- Content types: `application/json`

#### Response Shape

```json
{
  "active": "int",
  "decommissioned": "int",
  "unsubmitted": "int"
}
```

## Endpoint Tests

### `GET /users/self/alphas/summary`

- Status: `tested`
- Tested path: `/users/self/alphas/summary`
- HTTP: `200 OK`
- Elapsed: `514 ms`
- Content-Type: `application/json`
- Allow: `GET, HEAD, OPTIONS`

#### Tested Response Shape

```json
{
  "is": "int",
  "os": "int",
  "prod": "int"
}
```
