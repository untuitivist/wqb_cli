# `/data-sets`

- URL template: `https://api.worldquantbrain.com/data-sets`
- Methods: `GET`
- Sources: `platform_dynamic_capture, platform_frontend, rocky-d/wqb`
- Safe probe: `True`
- Description: Data set search. / Discovered from platform frontend bundle.
- Params: `{"instrumentType": "EQUITY", "region": "region", "delay": "delay", "universe": "universe", "limit": "1..100", "offset": "0..10000", "theme": "observed query parameter"}`

## Probe

- Probe URL: `https://api.worldquantbrain.com/data-sets?instrumentType=EQUITY&region=USA&delay=1&universe=TOP3000&limit=1`
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
      "name": "str",
      "description": "str",
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
      "dateCoverage": "float",
      "coverage": "float",
      "valueScore": "float",
      "userCount": "int",
      "alphaCount": "int",
      "fieldCount": "int",
      "pyramidMultiplier": "float",
      "themes": [],
      "researchPapers": [
        "..."
      ]
    }
  ]
}
```

## Dynamic Capture

### `GET /data-sets`

- Seen count: `2`
- Status codes: `200`
- Query keys: `delay, instrumentType, limit, offset, region, theme, universe`
- Content types: `application/json`

#### Response Shape

```json
{
  "count": "int",
  "results": []
}
```

## Endpoint Tests

### `GET /data-sets`

- Status: `tested`
- Tested path: `/data-sets`
- HTTP: `200 OK`
- Elapsed: `1032 ms`
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
      "dateCoverage": "float",
      "delay": "int",
      "description": "str",
      "fieldCount": "int",
      "id": "str",
      "name": "str",
      "pyramidMultiplier": "float",
      "region": "str",
      "researchPapers": [
        "dict"
      ],
      "subcategory": {
        "id": "str",
        "name": "str"
      },
      "themes": [],
      "universe": "str",
      "userCount": "int",
      "valueScore": "float"
    }
  ]
}
```
