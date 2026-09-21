# `/authentication/workday`

- URL template: `https://api.worldquantbrain.com/authentication/workday`
- Methods: `GET`
- Sources: `platform_frontend`
- Safe probe: `True`
- Description: Discovered from platform frontend bundle.

## Probe

- Probe URL: `https://api.worldquantbrain.com/authentication/workday`
- Allowed methods: `GET, POST, HEAD, OPTIONS`
- Status: `200 OK`
- Usable GET: `True`

### Response Shape

```json
"text"
```

## Endpoint Tests

### `GET /authentication/workday`

- Status: `tested`
- Tested path: `/authentication/workday`
- HTTP: `302 Found`
- Elapsed: `260 ms`
- Allow: `GET, POST, HEAD, OPTIONS`

## API refresh 2026-09-22

Discovered from platform frontend bundle.

- Advertised methods: GET, HEAD, OPTIONS, POST.
- Live OPTIONS status: 200. Mutation methods were not executed.
- Account-specific option values are omitted; use `wqb api call` with OPTIONS for current metadata.
