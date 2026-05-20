# `/simulations/{simulation_id}`

- URL template: `https://api.worldquantbrain.com/simulations/{simulation_id}`
- Methods: `GET`
- Sources: `observed_platform`
- Safe probe: `False`
- Description: Simulation status/details.

## Probe

- Skipped

## Official Notes

```json
{
  "summary": "获取 simulation 当前状态。",
  "methods": {
    "GET": {
      "description": "查询 simulation 进度或完成结果。",
      "in_progress": "返回 Retry-After 和 progress。",
      "complete": "返回 id、parent、children、status、message、location、progress、alpha 等字段。"
    }
  }
}
```

## Endpoint Tests

### `GET /simulations/{simulation_id}`

- Status: `tested`
- Tested path: `/simulations/2UnwIe7g5jEcCgDvI4GpqO`
- HTTP: `200 OK`
- Elapsed: `275 ms`
- Content-Type: `application/json`
- Allow: `GET, DELETE, HEAD, OPTIONS`

#### Tested Response Shape

```json
{
  "alpha": "str",
  "id": "str",
  "links": {
    "linkToCommonErrorMessages": "str"
  },
  "location": {
    "property": "str",
    "type": "str"
  },
  "message": "str",
  "regular": "str",
  "settings": {
    "decay": "int",
    "delay": "int",
    "instrumentType": "str",
    "language": "str",
    "maxPosition": "str",
    "maxTrade": "str",
    "nanHandling": "str",
    "neutralization": "str",
    "pasteurization": "str",
    "region": "str",
    "truncation": "float",
    "unitHandling": "str",
    "universe": "str",
    "visualization": "bool"
  },
  "status": "str",
  "type": "str"
}
```
