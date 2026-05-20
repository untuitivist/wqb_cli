# `/data-sets/{dataset_id}`

- URL template: `https://api.worldquantbrain.com/data-sets/{dataset_id}`
- Methods: `GET`
- Sources: `rocky-d/wqb`
- Safe probe: `False`
- Description: Dataset details.

## Probe

- Skipped

## Endpoint Tests

### `GET /data-sets/{dataset_id}`

- Status: `tested`
- Tested path: `/data-sets/analyst10`
- HTTP: `200 OK`
- Elapsed: `5075 ms`
- Content-Type: `application/json`
- Allow: `GET, HEAD, OPTIONS`

#### Tested Response Shape

```json
{
  "category": {
    "id": "str",
    "name": "str"
  },
  "data": [
    {
      "alphaCount": "int",
      "coverage": "float",
      "dateCoverage": "float",
      "delay": "int",
      "fieldCount": "int",
      "pyramidMultiplier": "float",
      "region": "str",
      "themes": [],
      "universe": "str",
      "userCount": "int",
      "valueScore": "float"
    }
  ],
  "description": "str",
  "id": "str",
  "name": "str",
  "researchPapers": [
    {
      "title": "str",
      "type": "str",
      "url": "str"
    }
  ],
  "subcategory": {
    "id": "str",
    "name": "str"
  }
}
```
