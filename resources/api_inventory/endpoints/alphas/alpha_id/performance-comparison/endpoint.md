# `/alphas/{alpha_id}/performance-comparison`

- URL template: `https://api.worldquantbrain.com/alphas/{alpha_id}/performance-comparison`
- Methods: `GET`
- Sources: `observed_platform`
- Safe probe: `False`
- Description: Before/after performance comparison.

## Probe

- Skipped

## Endpoint Tests

### `GET /alphas/{alpha_id}/performance-comparison`

- Status: `tested`
- Tested path: `/alphas/vR5p8vqb/performance-comparison`
- HTTP: `404 Not Found`
- Elapsed: `257 ms`
- Content-Type: `application/json`

#### Tested Response Shape

```json
{
  "detail": "str"
}
```

## API refresh 2026-09-22

Before/after performance comparison.

- Advertised methods: GET.
- Live OPTIONS status: 404. Mutation methods were not executed.
- Account-specific option values are omitted; use `wqb api call` with OPTIONS for current metadata.
