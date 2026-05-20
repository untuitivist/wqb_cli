# `/users/{user_id}/settings/simulation`

- URL template: `https://api.worldquantbrain.com/users/{user_id}/settings/simulation`
- Methods: `GET`
- Sources: `platform_dynamic_capture`
- Safe probe: `True`
- Description: Observed by passive platform network capture.

## Probe

- Skipped/Error: `Observed by platform dynamic network capture; no separate safe probe was run.`

## Dynamic Capture

### `GET /users/JL40454/settings/simulation`

- Seen count: `14`
- Status codes: `200`
- Query keys: ``
- Content types: `application/json`

#### Response Shape

```json
{
  "componentActivation": "str",
  "decay": "int",
  "delay": "int",
  "instrumentType": "str",
  "language": "str",
  "lookback": "int",
  "maxPosition": "str",
  "maxTrade": "str",
  "neutralization": "str",
  "region": "str",
  "selectionHandling": "str",
  "selectionLimit": "int",
  "testPeriod": "str",
  "truncation": "float",
  "universe": "str",
  "visualization": "bool"
}
```

## Endpoint Tests

### `GET /users/{user_id}/settings/simulation`

- Status: `tested`
- Tested path: `/users/JL40454/settings/simulation`
- HTTP: `200 OK`
- Elapsed: `262 ms`
- Content-Type: `application/json`
- Allow: `GET, POST, HEAD, OPTIONS`

#### Tested Response Shape

```json
{
  "componentActivation": "str",
  "decay": "int",
  "delay": "int",
  "instrumentType": "str",
  "language": "str",
  "lookback": "int",
  "maxPosition": "str",
  "maxTrade": "str",
  "neutralization": "str",
  "region": "str",
  "selectionHandling": "str",
  "selectionLimit": "int",
  "testPeriod": "str",
  "truncation": "float",
  "universe": "str",
  "visualization": "bool"
}
```
