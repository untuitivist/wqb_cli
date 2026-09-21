# `/agreements`

- URL template: `https://api.worldquantbrain.com/agreements`
- Methods: `GET`
- Sources: `platform_frontend`
- Safe probe: `True`
- Description: Agreements. / Discovered from platform frontend bundle.

## Probe

- Probe URL: `https://api.worldquantbrain.com/agreements`
- Allowed methods: `GET, POST, HEAD, OPTIONS`
- Status: `405 Method Not Allowed`
- Usable GET: `False`

### Response Shape

```json
{
  "detail": "str"
}
```

## Endpoint Tests

### `GET /agreements`

- Status: `tested`
- Tested path: `/agreements`
- HTTP: `405 Method Not Allowed`
- Elapsed: `262 ms`
- Content-Type: `application/json`
- Allow: `GET, POST, HEAD, OPTIONS`

#### Tested Response Shape

```json
{
  "detail": "str"
}
```

## API refresh 2026-09-22

Agreements. / Discovered from platform frontend bundle.

- Advertised methods: GET, HEAD, OPTIONS, POST.
- Live OPTIONS status: 200. Mutation methods were not executed.
- Account-specific option values are omitted; use `wqb api call` with OPTIONS for current metadata.
