# `/competition-levels`

- URL template: `https://api.worldquantbrain.com/competition-levels`
- Methods: `GET`
- Sources: `platform_dynamic_capture, platform_frontend`
- Safe probe: `True`
- Description: Competition levels. / Discovered from platform frontend bundle.

## Probe

- Probe URL: `https://api.worldquantbrain.com/competition-levels`
- Allowed methods: `GET, HEAD, OPTIONS`
- Status: `200 OK`
- Usable GET: `True`

### Response Shape

```json
[
  {
    "id": "str",
    "name": "str"
  }
]
```

## Dynamic Capture

### `GET /competition-levels`

- Seen count: `1`
- Status codes: `200`
- Query keys: ``
- Content types: `application/json`

#### Response Shape

```json
[
  {
    "id": "str",
    "name": "str"
  }
]
```

## Endpoint Tests

### `GET /competition-levels`

- Status: `tested`
- Tested path: `/competition-levels`
- HTTP: `200 OK`
- Elapsed: `372 ms`
- Content-Type: `application/json`
- Allow: `GET, HEAD, OPTIONS`

#### Tested Response Shape

```json
[
  {
    "id": "str",
    "name": "str"
  }
]
```
