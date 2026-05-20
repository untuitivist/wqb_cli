# `/data-categories`

- URL template: `https://api.worldquantbrain.com/data-categories`
- Methods: `GET`
- Sources: `platform_dynamic_capture, platform_frontend, rocky-d/wqb`
- Safe probe: `True`
- Description: Data categories. / Discovered from platform frontend bundle.

## Probe

- Probe URL: `https://api.worldquantbrain.com/data-categories`
- Allowed methods: `GET, HEAD, OPTIONS`
- Status: `200 OK`
- Usable GET: `True`

### Response Shape

```json
[
  {
    "id": "str",
    "name": "str",
    "datasetCount": "int",
    "fieldCount": "int",
    "alphaCount": "int",
    "userCount": "int",
    "valueScore": "float",
    "region": [
      "str"
    ],
    "children": [
      {
        "id": "...",
        "name": "...",
        "datasetCount": "...",
        "fieldCount": "...",
        "alphaCount": "...",
        "userCount": "...",
        "valueScore": "...",
        "region": "..."
      }
    ]
  }
]
```

## Dynamic Capture

### `GET /data-categories`

- Seen count: `3`
- Status codes: `200`
- Query keys: ``
- Content types: `application/json`

#### Response Shape

```json
[
  {
    "alphaCount": "int",
    "children": [
      {
        "alphaCount": "int",
        "datasetCount": "int",
        "fieldCount": "int",
        "id": "str",
        "name": "str",
        "region": "list",
        "userCount": "int",
        "valueScore": "float"
      }
    ],
    "datasetCount": "int",
    "fieldCount": "int",
    "id": "str",
    "name": "str",
    "region": [
      "str"
    ],
    "userCount": "int",
    "valueScore": "float"
  }
]
```

## Endpoint Tests

### `GET /data-categories`

- Status: `tested`
- Tested path: `/data-categories`
- HTTP: `200 OK`
- Elapsed: `1270 ms`
- Content-Type: `application/json`
- Allow: `GET, HEAD, OPTIONS`

#### Tested Response Shape

```json
[
  {
    "alphaCount": "int",
    "children": [
      {
        "alphaCount": "int",
        "datasetCount": "int",
        "fieldCount": "int",
        "id": "str",
        "name": "str",
        "region": "list",
        "userCount": "int",
        "valueScore": "float"
      }
    ],
    "datasetCount": "int",
    "fieldCount": "int",
    "id": "str",
    "name": "str",
    "region": [
      "str"
    ],
    "userCount": "int",
    "valueScore": "float"
  }
]
```
