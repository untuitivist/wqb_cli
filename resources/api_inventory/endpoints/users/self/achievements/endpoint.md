# `/users/self/achievements`

- URL template: `https://api.worldquantbrain.com/users/self/achievements`
- Methods: `GET`
- Sources: `platform_dynamic_capture`
- Safe probe: `True`
- Description: Observed by passive platform network capture.

## Probe

- Skipped/Error: `Observed by platform dynamic network capture; no separate safe probe was run.`

## Dynamic Capture

### `GET /users/self/achievements`

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

### `GET /users/self/achievements`

- Status: `tested`
- Tested path: `/users/self/achievements`
- HTTP: `200 OK`
- Elapsed: `621 ms`
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
