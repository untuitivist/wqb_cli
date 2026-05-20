# `/data-fields`

- URL template: `https://api.worldquantbrain.com/data-fields`
- Methods: `GET`
- Sources: `platform_dynamic_capture, platform_frontend, rocky-d/wqb`
- Safe probe: `True`
- Description: Data field search. / Discovered from platform frontend bundle.
- Params: `{"dataset.id": "dataset id", "search": "query", "limit": "1..100", "offset": "0..10000", "delay": "observed query parameter", "instrumentType": "observed query parameter", "region": "observed query parameter", "universe": "observed query parameter"}`

## Probe

- Probe URL: `https://api.worldquantbrain.com/data-fields?instrumentType=EQUITY&region=USA&delay=1&universe=TOP3000&limit=1`
- Allowed methods: `GET, HEAD, OPTIONS`
- Status: `200 OK`
- Usable GET: `True`

### Response Shape

```json
{
  "count": "int",
  "results": [
    {
      "id": "str",
      "description": "str",
      "dataset": {
        "id": "...",
        "name": "..."
      },
      "category": {
        "id": "...",
        "name": "..."
      },
      "subcategory": {
        "id": "...",
        "name": "..."
      },
      "region": "str",
      "delay": "int",
      "universe": "str",
      "type": "str",
      "dateCoverage": "float",
      "coverage": "float",
      "userCount": "int",
      "alphaCount": "int",
      "pyramidMultiplier": "float",
      "themes": []
    }
  ]
}
```

## Dynamic Capture

### `GET /data-fields`

- Seen count: `9`
- Status codes: `200`
- Query keys: `delay, instrumentType, limit, offset, region, universe`
- Content types: `application/json`

#### Response Shape

```json
{
  "count": "int",
  "results": [
    {
      "alphaCount": "int",
      "category": {
        "id": "str",
        "name": "str"
      },
      "coverage": "float",
      "dataset": {
        "id": "str",
        "name": "str"
      },
      "dateCoverage": "float",
      "delay": "int",
      "description": "str",
      "id": "str",
      "pyramidMultiplier": "float",
      "region": "str",
      "subcategory": {
        "id": "str",
        "name": "str"
      },
      "themes": [],
      "type": "str",
      "universe": "str",
      "userCount": "int"
    }
  ]
}
```

## Endpoint Tests

### `GET /data-fields`

- Status: `tested`
- Tested path: `/data-fields`
- HTTP: `200 OK`
- Elapsed: `255 ms`
- Content-Type: `application/json`
- Allow: `GET, HEAD, OPTIONS`

#### Tested Response Shape

```json
{
  "count": "int",
  "results": [
    {
      "alphaCount": "int",
      "category": {
        "id": "str",
        "name": "str"
      },
      "coverage": "float",
      "dataset": {
        "id": "str",
        "name": "str"
      },
      "dateCoverage": "float",
      "delay": "int",
      "description": "str",
      "id": "str",
      "pyramidMultiplier": "float",
      "region": "str",
      "subcategory": {
        "id": "str",
        "name": "str"
      },
      "themes": [],
      "type": "str",
      "universe": "str",
      "userCount": "int"
    }
  ]
}
```
