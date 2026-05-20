# `/alphas/{alpha_id}/correlations/self`

- URL template: `https://api.worldquantbrain.com/alphas/{alpha_id}/correlations/self`
- Methods: `GET`
- Sources: `observed_platform`
- Safe probe: `False`
- Description: Self correlation.

## Probe

- Skipped

## Endpoint Tests

### `GET /alphas/{alpha_id}/correlations/self`

- Status: `tested`
- Tested path: `/alphas/vR5p8vqb/correlations/self`
- HTTP: `200 OK`
- Elapsed: `261 ms`
- Content-Type: `application/json`
- Allow: `GET, HEAD, OPTIONS`

#### Tested Response Shape

```json
{
  "max": "float",
  "min": "float",
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
