# `/users/self/teams`

- URL template: `https://api.worldquantbrain.com/users/self/teams`
- Methods: `GET`
- Sources: `platform_dynamic_capture`
- Safe probe: `True`
- Description: Observed by passive platform network capture.
- Params: `{"members.self.status": "observed query parameter", "order": "observed query parameter", "status": "observed query parameter"}`

## Probe

- Skipped/Error: `Observed by platform dynamic network capture; no separate safe probe was run.`

## Dynamic Capture

### `GET /users/self/teams`

- Seen count: `42`
- Status codes: `200`
- Query keys: `members.self.status, order, status`
- Content types: `application/json`

#### Response Shape

```json
{
  "count": "int",
  "next": "null",
  "previous": "null",
  "results": []
}
```

## Endpoint Tests

### `GET /users/self/teams`

- Status: `tested`
- Tested path: `/users/self/teams`
- HTTP: `200 OK`
- Elapsed: `256 ms`
- Content-Type: `application/json`
- Allow: `GET, HEAD, OPTIONS`

#### Tested Response Shape

```json
{
  "count": "int",
  "next": "null",
  "previous": "null",
  "results": []
}
```
