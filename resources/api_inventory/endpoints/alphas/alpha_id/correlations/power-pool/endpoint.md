# `/alphas/{alpha_id}/correlations/power-pool`

- URL template: `https://api.worldquantbrain.com/alphas/{alpha_id}/correlations/power-pool`
- Methods: `GET`
- Sources: `observed_platform`
- Safe probe: `False`
- Description: Power Pool correlation.

## Probe

- Skipped

## Endpoint Tests

### `GET /alphas/{alpha_id}/correlations/power-pool`

- Status: `tested`
- Tested path: `/alphas/vR5p8vqb/correlations/power-pool`
- HTTP: `200 OK`
- Elapsed: `329 ms`
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
