# `/data-fields/{field_id}`

- URL template: `https://api.worldquantbrain.com/data-fields/{field_id}`
- Methods: `GET`
- Sources: `rocky-d/wqb`
- Safe probe: `False`
- Description: Data field details.

## Probe

- Skipped

## Endpoint Tests

### `GET /data-fields/{field_id}`

- Status: `tested`
- Tested path: `/data-fields/abnormal_news_sentiment_1d`
- HTTP: `200 OK`
- Elapsed: `561 ms`
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
      "pyramidMultiplier": "float",
      "region": "str",
      "themes": [],
      "universe": "str",
      "userCount": "int"
    }
  ],
  "dataset": {
    "id": "str",
    "name": "str"
  },
  "description": "str",
  "id": "str",
  "subcategory": {
    "id": "str",
    "name": "str"
  },
  "type": "str",
  "visualizable": "bool"
}
```

## API refresh 2026-09-22

Data field details.

- Advertised methods: GET, HEAD.
- Live OPTIONS status: 400. Mutation methods were not executed.
- Account-specific option values are omitted; use `wqb api call` with OPTIONS for current metadata.
