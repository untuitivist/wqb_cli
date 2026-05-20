# `/achievements`

- URL template: `https://api.worldquantbrain.com/achievements`
- Methods: `GET`
- Sources: `platform_frontend`
- Safe probe: `True`
- Description: Achievements. / Discovered from platform frontend bundle.

## Probe

- Probe URL: `https://api.worldquantbrain.com/achievements`
- Allowed methods: `GET, HEAD, OPTIONS`
- Status: `200 OK`
- Usable GET: `True`

### Response Shape

```json
[
  {
    "id": "str",
    "name": "str",
    "description": "str",
    "total": "int"
  }
]
```

## Endpoint Tests

### `GET /achievements`

- Status: `tested`
- Tested path: `/achievements`
- HTTP: `200 OK`
- Elapsed: `255 ms`
- Content-Type: `application/json`
- Allow: `GET, HEAD, OPTIONS`

#### Tested Response Shape

```json
[
  {
    "description": "str",
    "id": "str",
    "name": "str",
    "total": "int"
  }
]
```
