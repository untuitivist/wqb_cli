# `/users/self/agreements`

- URL template: `https://api.worldquantbrain.com/users/self/agreements`
- Methods: `GET`
- Sources: `platform_dynamic_capture`
- Safe probe: `True`
- Description: Observed by passive platform network capture.

## Probe

- Skipped/Error: `Observed by platform dynamic network capture; no separate safe probe was run.`

## Dynamic Capture

### `GET /users/self/agreements`

- Seen count: `14`
- Status codes: `200`
- Query keys: ``
- Content types: `application/json`

#### Response Shape

```json
[
  {
    "agreement": {
      "id": "str",
      "name": "str"
    },
    "status": "str",
    "statusDate": "str"
  }
]
```

## Endpoint Tests

### `GET /users/self/agreements`

- Status: `tested`
- Tested path: `/users/self/agreements`
- HTTP: `200 OK`
- Elapsed: `288 ms`
- Content-Type: `application/json`
- Allow: `GET, HEAD, OPTIONS`

#### Tested Response Shape

```json
[
  {
    "agreement": {
      "id": "str",
      "name": "str"
    },
    "status": "str",
    "statusDate": "str"
  }
]
```
