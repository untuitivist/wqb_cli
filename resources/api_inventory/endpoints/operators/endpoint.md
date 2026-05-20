# `/operators`

- URL template: `https://api.worldquantbrain.com/operators`
- Methods: `GET`
- Sources: `platform_dynamic_capture, platform_frontend, rocky-d/wqb`
- Safe probe: `True`
- Description: Operator list/search. / Discovered from platform frontend bundle.
- Params: `{"instrumentType": "optional", "region": "optional", "delay": "optional"}`

## Probe

- Probe URL: `https://api.worldquantbrain.com/operators`
- Allowed methods: `GET, HEAD, OPTIONS`
- Status: `200 OK`
- Usable GET: `True`

### Response Shape

```json
[
  {
    "name": "str",
    "category": "str",
    "scope": [
      "str"
    ],
    "definition": "str",
    "description": "str",
    "documentation": "str",
    "level": "str"
  }
]
```

## Dynamic Capture

### `GET /operators`

- Seen count: `15`
- Status codes: `200`
- Query keys: ``
- Content types: `application/json`

#### Response Shape

```json
[
  {
    "category": "str",
    "definition": "str",
    "description": "str",
    "documentation": "str",
    "level": "str",
    "name": "str",
    "scope": [
      "str"
    ]
  }
]
```

## Endpoint Tests

### `GET /operators`

- Status: `tested`
- Tested path: `/operators`
- HTTP: `200 OK`
- Elapsed: `298 ms`
- Content-Type: `application/json`
- Allow: `GET, HEAD, OPTIONS`

#### Tested Response Shape

```json
[
  {
    "category": "str",
    "definition": "str",
    "description": "str",
    "documentation": "str",
    "level": "str",
    "name": "str",
    "scope": [
      "str"
    ]
  }
]
```
