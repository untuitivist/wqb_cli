# `/alphas/{alpha_id}/recordsets`

- URL template: `https://api.worldquantbrain.com/alphas/{alpha_id}/recordsets`
- Methods: `GET`
- Sources: `observed_platform`
- Safe probe: `False`
- Description: Alpha recordset index.

## Probe

- Skipped

## Official Notes

```json
{
  "summary": "列出 alpha 可用 record sets。",
  "methods": {
    "GET": {
      "description": "返回 count 和 results，results 中包含 name 与 title。",
      "known_recordsets": [
        "pnl",
        "sharpe",
        "turnover",
        "daily-pnl",
        "yearly-stats",
        "coverage",
        "coverage-by-industry",
        "coverage-by-sector",
        "average-size-by-industry",
        "average-size-by-sector",
        "average-size-by-capitalization",
        "pnl-by-industry",
        "pnl-by-sector",
        "pnl-by-capitalization",
        "sharpe-by-industry",
        "sharpe-by-sector",
        "sharpe-by-capitalization",
        "average-value-by-industry",
        "average-value-by-sector"
      ]
    }
  }
}
```

## Endpoint Tests

### `GET /alphas/{alpha_id}/recordsets`

- Status: `tested`
- Tested path: `/alphas/vR5p8vqb/recordsets`
- HTTP: `200 OK`
- Elapsed: `289 ms`
- Content-Type: `application/json`
- Allow: `GET, HEAD, OPTIONS`

#### Tested Response Shape

```json
{
  "count": "int",
  "next": "null",
  "previous": "null",
  "results": [
    {
      "name": "str",
      "title": "str"
    }
  ]
}
```
