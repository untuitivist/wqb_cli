# `/consultant-datasets`

- URL template: `https://api.worldquantbrain.com/consultant-datasets`
- Methods: `GET`
- Sources: `platform_frontend`
- Safe probe: `True`
- Description: Consultant datasets. / Discovered from platform frontend bundle.

## Probe

- Probe URL: `https://api.worldquantbrain.com/consultant-datasets`
- Status: `404 Not Found`
- Usable GET: `False`

### Response Shape

```json
{
  "detail": "str"
}
```

## Endpoint Tests

### `GET /consultant-datasets`

- Status: `tested`
- Tested path: `/consultant-datasets`
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

Consultant datasets. / Discovered from platform frontend bundle.

- Advertised methods: GET.
- Live OPTIONS status: 404. Mutation methods were not executed.
- Account-specific option values are omitted; use `wqb api call` with OPTIONS for current metadata.
