# `/alphas/{alpha_id}/recordsets/pnl`

- URL template: `https://api.worldquantbrain.com/alphas/{alpha_id}/recordsets/pnl`
- Methods: `GET`
- Sources: `observed_platform`
- Safe probe: `False`
- Description: PNL recordset.

## Probe

- Skipped

## Official Notes

```json
{
  "summary": "获取指定 record set。",
  "methods": {
    "GET": {
      "description": "不同 record set 返回不同 schema 与 records。records 是紧凑表格编码。",
      "recordset_format": {
        "schema": "name, title, properties[]",
        "records": "array of row arrays matching schema.properties"
      }
    }
  }
}
```

## Endpoint Tests

### `GET /alphas/{alpha_id}/recordsets/pnl`

- Status: `tested`
- Tested path: `/alphas/vR5p8vqb/recordsets/pnl`
- HTTP: `200 OK`
- Elapsed: `390 ms`
- Content-Type: `application/json`
- Allow: `GET, HEAD, OPTIONS`

#### Tested Response Shape

```json
{
  "records": [
    [
      "str"
    ]
  ],
  "schema": {
    "name": "str",
    "properties": [
      {
        "name": "str",
        "title": "str",
        "type": "str"
      }
    ],
    "title": "str"
  }
}
```
