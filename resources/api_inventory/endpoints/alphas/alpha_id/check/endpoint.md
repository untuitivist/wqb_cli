# `/alphas/{alpha_id}/check`

- URL template: `https://api.worldquantbrain.com/alphas/{alpha_id}/check`
- Methods: `GET`
- Sources: `rocky-d/wqb`
- Safe probe: `False`
- Description: Alpha simulation check.

## Probe

- Skipped

## Endpoint Tests

### `GET /alphas/{alpha_id}/check`

- Status: `tested`
- Tested path: `/alphas/vR5p8vqb/check`
- HTTP: `200 OK`
- Elapsed: `617 ms`
- Content-Type: `application/json`
- Allow: `GET, PUT, PATCH, HEAD, OPTIONS`

#### Tested Response Shape

```json
{
  "is": {
    "checks": [
      {
        "limit": "float",
        "name": "str",
        "result": "str",
        "value": "float"
      }
    ]
  }
}
```

## API refresh 2026-09-22

Alpha simulation check.

- Advertised methods: GET, HEAD, OPTIONS, PATCH, PUT.
- Live OPTIONS status: 200. Mutation methods were not executed.
- Account-specific option values are omitted; use `wqb api call` with OPTIONS for current metadata.
