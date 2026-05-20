# `/alphas/{alpha_id}/correlations/prod`

- URL template: `https://api.worldquantbrain.com/alphas/{alpha_id}/correlations/prod`
- Methods: `GET`
- Sources: `observed_platform`
- Safe probe: `False`
- Description: Production correlation.

## Probe

- Skipped

## Endpoint Tests

### `GET /alphas/{alpha_id}/correlations/prod`

- Status: `tested`
- Tested path: `/alphas/vR5p8vqb/correlations/prod`
- HTTP: `200 OK`
- Elapsed: `271 ms`
- Content-Type: `application/json`
- Allow: `GET, HEAD, OPTIONS`

#### Tested Response Shape

```json
{
  "max": "float",
  "min": "float",
  "records": [
    [
      "float"
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
