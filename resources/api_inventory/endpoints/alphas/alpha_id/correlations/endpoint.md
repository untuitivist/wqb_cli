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

## API refresh 2026-09-22

Alpha correlation base endpoint.

- Advertised methods: GET.
- Live OPTIONS status: 404. Mutation methods were not executed.
- Account-specific option values are omitted; use `wqb api call` with OPTIONS for current metadata.
