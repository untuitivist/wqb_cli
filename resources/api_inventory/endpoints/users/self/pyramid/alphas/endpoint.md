# `/users/self/pyramid/alphas`

- URL template: `https://api.worldquantbrain.com/users/self/pyramid/alphas`
- Methods: `GET`
- Sources: `observed_platform`
- Safe probe: `True`
- Description: Fallback pyramid alpha endpoint.
- Params: `{"startDate": "YYYY-MM-DD", "endDate": "YYYY-MM-DD"}`

## Probe

- Probe URL: `https://api.worldquantbrain.com/users/self/pyramid/alphas`
- Status: `404 Not Found`
- Usable GET: `False`

### Response Shape

```json
{
  "detail": "str"
}
```

## Endpoint Tests

### `GET /users/self/pyramid/alphas`

- Status: `tested`
- Tested path: `/users/self/pyramid/alphas`
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

Fallback pyramid alpha endpoint.

- Advertised methods: GET.
- Live OPTIONS status: 404. Mutation methods were not executed.
- Account-specific option values are omitted; use `wqb api call` with OPTIONS for current metadata.
