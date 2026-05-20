# `/alphas/{alpha_id}`

- URL template: `https://api.worldquantbrain.com/alphas/{alpha_id}`
- Methods: `GET, PATCH`
- Sources: `platform_frontend, rocky-d/wqb`
- Safe probe: `False`
- Description: Alpha details or property patch. / Discovered from platform frontend bundle.
- Request body: PATCH updates alpha properties.

## Probe

- Skipped

## Official Notes

```json
{
  "summary": "获取 alpha 详情。alpha id 通常来自 simulation 完成结果里的 alpha 字段。",
  "methods": {
    "GET": {
      "description": "返回 alpha 的 type、settings、regular/combo/selection、is/os/prod 等信息。"
    }
  }
}
```

## Endpoint Tests

### `GET /alphas/{alpha_id}`

- Status: `tested`
- Tested path: `/alphas/vR5p8vqb`
- HTTP: `200 OK`
- Elapsed: `348 ms`
- Content-Type: `application/json`
- Allow: `GET, PUT, PATCH, HEAD, OPTIONS`

#### Tested Response Shape

```json
{
  "author": "str",
  "category": "null",
  "classifications": [
    {
      "id": "str",
      "name": "str"
    }
  ],
  "color": "null",
  "competitions": "null",
  "dateCreated": "str",
  "dateModified": "str",
  "dateSubmitted": "null",
  "favorite": "bool",
  "grade": "null",
  "hidden": "bool",
  "id": "str",
  "is": {
    "bookSize": "int",
    "checks": [
      {
        "limit": "float",
        "name": "str",
        "result": "str",
        "value": "float"
      }
    ],
    "drawdown": "float",
    "fitness": "float",
    "investabilityConstrained": {
      "bookSize": "int",
      "drawdown": "float",
      "fitness": "float",
      "longCount": "int",
      "margin": "float",
      "pnl": "int",
      "returns": "float",
      "sharpe": "float",
      "shortCount": "int",
      "turnover": "float"
    },
    "longCount": "int",
    "margin": "float",
    "pnl": "int",
    "returns": "float",
    "riskNeutralized": {
      "bookSize": "int",
      "drawdown": "float",
      "fitness": "float",
      "longCount": "int",
      "margin": "float",
      "pnl": "int",
      "returns": "float",
      "sharpe": "float",
      "shortCount": "int",
      "turnover": "float"
    },
    "sharpe": "float",
    "shortCount": "int",
    "startDate": "str",
    "turnover": "float"
  },
  "name": "null",
  "origin": "str",
  "os": "null",
  "osmosisPoints": "null",
  "prod": "null",
  "pyramidThemes": "null",
  "pyramids": "null",
  "regular": {
    "code": "str",
    "description": "null",
    "operatorCount": "int"
  },
  "settings": {
    "decay": "int",
    "delay": "int",
    "endDate": "str",
    "instrumentType": "str",
    "language": "str",
    "maxPosition": "str",
    "maxTrade": "str",
    "nanHandling": "str",
    "neutralization": "str",
    "pasteurization": "str",
    "region": "str",
    "startDate": "str",
    "testPeriod": "str",
    "truncation": "float",
    "unitHandling": "str",
    "universe": "str",
    "visualization": "bool"
  },
  "stage": "str",
  "status": "str",
  "tags": [],
  "team": "null",
  "test": {
    "bookSize": "int",
    "drawdown": "float",
    "fitness": "float",
    "investabilityConstrained": {
      "bookSize": "int",
      "drawdown": "float",
      "fitness": "float",
      "longCount": "int",
      "margin": "float",
      "pnl": "int",
      "returns": "float",
      "sharpe": "float",
      "shortCount": "int",
      "turnover": "float"
    },
    "longCount": "int",
    "margin": "float",
    "pnl": "int",
    "returns": "float",
    "riskNeutralized": {
      "bookSize": "int",
      "drawdown": "float",
      "fitness": "float",
      "longCount": "int",
      "margin": "float",
      "pnl": "int",
      "returns": "float",
      "sharpe": "float",
      "shortCount": "int",
      "turnover": "float"
    },
    "sharpe": "float",
    "shortCount": "int",
    "startDate": "str",
    "turnover": "float"
  },
  "themes": "null",
  "train": {
    "bookSize": "int",
    "drawdown": "float",
    "fitness": "float",
    "investabilityConstrained": {
      "bookSize": "int",
      "drawdown": "float",
      "fitness": "float",
      "longCount": "int",
      "margin": "float",
      "pnl": "int",
      "returns": "float",
      "sharpe": "float",
      "shortCount": "int",
      "turnover": "float"
    },
    "longCount": "int",
    "margin": "float",
    "pnl": "int",
    "returns": "float",
    "riskNeutralized": {
      "bookSize": "int",
      "drawdown": "float",
      "fitness": "float",
      "longCount": "int",
      "margin": "float",
      "pnl": "int",
      "returns": "float",
      "sharpe": "float",
      "shortCount": "int",
      "turnover": "float"
    },
    "sharpe": "float",
    "shortCount": "int",
    "startDate": "str",
    "turnover": "float"
  },
  "type": "str"
}
```
### `PATCH /alphas/{alpha_id}`

- Status: `skipped_mutating`
- Tested path: `/alphas/vR5p8vqb`
- Reason: PATCH may mutate remote state; not executed by inventory test.
