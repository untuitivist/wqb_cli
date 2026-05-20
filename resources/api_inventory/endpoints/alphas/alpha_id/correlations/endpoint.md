# `/alphas/{alpha_id}/correlations`

- URL template: `https://api.worldquantbrain.com/alphas/{alpha_id}/correlations`
- Methods: `GET`
- Sources: `observed_platform`
- Safe probe: `False`
- Description: Alpha correlation base endpoint.

## Probe

- Skipped

## Endpoint Tests

### `GET /alphas/{alpha_id}/correlations`

- Status: `tested`
- Tested path: `/alphas/vR5p8vqb/correlations`
- HTTP: `404 Not Found`
- Elapsed: `255 ms`
- Content-Type: `application/json`

#### Tested Response Shape

```json
{
  "detail": "str"
}
```
