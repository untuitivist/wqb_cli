# `/simulations/super-selection`

- URL template: `https://api.worldquantbrain.com/simulations/super-selection`
- Methods: `GET, POST`
- Sources: `observed_platform, platform_frontend`
- Safe probe: `False`
- Description: Super selection simulation. / Discovered from platform frontend bundle.
- Request body: POST creates simulation.

## Probe

- Skipped

## Endpoint Tests

### `GET /simulations/super-selection`

- Status: `tested`
- Tested path: `/simulations/super-selection`
- HTTP: `200 OK`
- Elapsed: `1657 ms`
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
      "author": "null",
      "category": "null",
      "classifications": [
        "dict"
      ],
      "color": "null",
      "competitions": [],
      "dateCreated": "str",
      "dateModified": "str",
      "dateSubmitted": "str",
      "favorite": "null",
      "grade": "null",
      "hidden": "null",
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
        "prodCorrelation": "float",
        "returns": "float",
        "riskNeutralized": "dict",
        "selfCorrelation": "float",
        "sharpe": "float",
        "shortCount": "int",
        "startDate": "str",
        "turnover": "float"
      },
      "name": "null",
      "origin": "str",
      "os": {
        "checks": "list",
        "osISSharpeRatio": "NoneType",
        "preCloseSharpeRatio": "NoneType",
        "startDate": "str"
      },
      "osmosisPoints": "null",
      "prod": "null",
      "pyramidThemes": "null",
      "pyramids": "null",
      "regular": {
        "code": "NoneType",
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
      "themes": [],
      "train": "null",
      "type": "str"
    }
  ]
}
```
### `POST /simulations/super-selection`

- Status: `skipped_mutating`
- Tested path: `/simulations/super-selection`
- Reason: POST may mutate remote state; not executed by inventory test.
