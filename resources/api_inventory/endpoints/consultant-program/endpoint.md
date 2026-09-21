# `/consultant-program`

- URL template: `https://api.worldquantbrain.com/consultant-program`
- Methods: `GET`
- Sources: `platform_frontend`
- Safe probe: `True`
- Description: Discovered from platform frontend bundle.

## Probe

- Probe URL: `https://api.worldquantbrain.com/consultant-program`
- Status: `404 Not Found`
- Usable GET: `False`

### Response Shape

```json
{
  "detail": "str"
}
```

## Endpoint Tests

### `GET /consultant-program`

- Status: `tested`
- Tested path: `/consultant-program`
- HTTP: `404 Not Found`
- Elapsed: `258 ms`
- Content-Type: `application/json`

#### Tested Response Shape

```json
{
  "detail": "str"
}
```

## API refresh 2026-09-22

Discovered from platform frontend bundle.

- Advertised methods: GET.
- Live OPTIONS status: 404. Mutation methods were not executed.
- Account-specific option values are omitted; use `wqb api call` with OPTIONS for current metadata.
