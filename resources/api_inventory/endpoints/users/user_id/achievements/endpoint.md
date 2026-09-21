# `/users/{user_id}/achievements`

- URL template: `https://api.worldquantbrain.com/users/{user_id}/achievements`
- Methods: `GET`
- Sources: `platform_dynamic_capture`
- Safe probe: `True`
- Description: Observed by passive platform network capture.

## Probe

- Skipped/Error: `Observed by platform dynamic network capture; no separate safe probe was run.`

## Dynamic Capture

### `GET /users/JL40454/achievements`

- Seen count: `1`
- Status codes: `200`
- Query keys: ``
- Content types: `application/json`

#### Response Shape

```json
[
  {
    "achieved": "str",
    "description": "str",
    "id": "str",
    "name": "str",
    "ratio": "float",
    "total": "int",
    "value": "int"
  }
]
```

## Endpoint Tests

### `GET /users/{user_id}/achievements`

- Status: `tested`
- Tested path: `/users/JL40454/achievements`
- HTTP: `200 OK`
- Elapsed: `614 ms`
- Content-Type: `application/json`
- Allow: `GET, HEAD, OPTIONS`

#### Tested Response Shape

```json
[
  {
    "achieved": "str",
    "description": "str",
    "id": "str",
    "name": "str",
    "ratio": "float",
    "total": "int",
    "value": "int"
  }
]
```

## API refresh 2026-09-22

Observed by passive platform network capture.

- Advertised methods: GET, HEAD.
- Live OPTIONS status: 405. Mutation methods were not executed.
- Account-specific option values are omitted; use `wqb api call` with OPTIONS for current metadata.
