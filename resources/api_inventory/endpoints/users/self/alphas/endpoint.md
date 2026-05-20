# `/users/self/alphas`

- URL template: `https://api.worldquantbrain.com/users/self/alphas`
- Methods: `GET`
- Sources: `rocky-d/wqb`
- Safe probe: `True`
- Description: Current user's alphas.
- Params: `{"limit": "1..100", "offset": "0..10000", "dateSubmitted": "range", "type": "REGULAR|SUPER", "color": "platform color", "tag": "tag filter"}`

## Probe

- Probe URL: `https://api.worldquantbrain.com/users/self/alphas?limit=1`
- Allowed methods: `GET, HEAD, OPTIONS`
- Status: `200 OK`
- Usable GET: `True`

### Response Shape

```json
{
  "count": "int",
  "next": "str",
  "previous": "NoneType",
  "results": [
    {
      "id": "str",
      "type": "str",
      "author": "str",
      "settings": {
        "instrumentType": "...",
        "region": "...",
        "universe": "...",
        "delay": "...",
        "decay": "...",
        "neutralization": "...",
        "truncation": "...",
        "pasteurization": "...",
        "unitHandling": "...",
        "nanHandling": "...",
        "maxTrade": "...",
        "maxPosition": "...",
        "language": "...",
        "visualization": "...",
        "startDate": "...",
        "endDate": "...",
        "testPeriod": "..."
      },
      "regular": {
        "code": "...",
        "description": "...",
        "operatorCount": "..."
      },
      "dateCreated": "str",
      "dateSubmitted": "NoneType",
      "dateModified": "str",
      "name": "NoneType",
      "favorite": "bool",
      "hidden": "bool",
      "color": "NoneType",
      "category": "NoneType",
      "tags": [],
      "classifications": [
        "..."
      ],
      "grade": "NoneType",
      "stage": "str",
      "status": "str",
      "is": {
        "pnl": "...",
        "bookSize": "...",
        "longCount": "...",
        "shortCount": "...",
        "turnover": "...",
        "returns": "...",
        "drawdown": "...",
        "margin": "...",
        "sharpe": "...",
        "fitness": "...",
        "startDate": "...",
        "investabilityConstrained": "...",
        "riskNeutralized": "...",
        "checks": "..."
      },
      "os": "NoneType",
      "train": {
        "pnl": "...",
        "bookSize": "...",
        "longCount": "...",
        "shortCount": "...",
        "turnover": "...",
        "returns": "...",
        "drawdown": "...",
        "margin": "...",
        "fitness": "...",
        "sharpe": "...",
        "startDate": "...",
        "investabilityConstrained": "...",
        "riskNeutralized": "..."
      },
      "test": {
        "pnl": "...",
        "bookSize": "...",
        "longCount": "...",
        "shortCount": "...",
        "turnover": "...",
        "returns": "...",
        "drawdown": "...",
        "margin": "...",
        "fitness": "...",
        "sharpe": "...",
        "startDate": "...",
        "investabilityConstrained": "...",
        "riskNeutralized": "..."
      },
      "prod": "NoneType",
      "competitions": "NoneType",
      "themes": "NoneType",
      "pyramids": "NoneType",
      "pyramidThemes": "NoneType",
      "team": "NoneType",
      "osmosisPoints": "NoneType",
      "origin": "str"
    }
  ]
}
```

## Endpoint Tests

### `GET /users/self/alphas`

- Status: `tested`
- Tested path: `/users/self/alphas`
- HTTP: `200 OK`
- Elapsed: `626 ms`
- Content-Type: `application/json`
- Allow: `GET, HEAD, OPTIONS`

#### Tested Response Shape

```json
{
  "count": "int",
  "next": "str",
  "previous": "null",
  "results": [
    {
      "author": "str",
      "category": "null",
      "classifications": [
        "dict"
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
        "checks": "list",
        "drawdown": "float",
        "fitness": "float",
        "investabilityConstrained": "dict",
        "longCount": "int",
        "margin": "float",
        "pnl": "int",
        "returns": "float",
        "riskNeutralized": "dict",
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
        "description": "NoneType",
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
        "truncation": "float",
        "unitHandling": "str",
        "universe": "str",
        "visualization": "bool"
      },
      "stage": "str",
      "status": "str",
      "tags": [],
      "team": "null",
      "test": "null",
      "themes": "null",
      "train": "null",
      "type": "str"
    }
  ]
}
```
