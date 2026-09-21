# `/users`

- URL template: `https://api.worldquantbrain.com/users`
- Methods: `GET`
- Sources: `platform_frontend`
- Safe probe: `True`
- Description: Users collection. / Discovered from platform frontend bundle.
- Params: `{"limit": "optional"}`

## Probe

- Probe URL: `https://api.worldquantbrain.com/users`
- Allowed methods: `POST, OPTIONS`
- Status: `405 Method Not Allowed`
- Usable GET: `False`

### Response Shape

```json
{
  "detail": "str"
}
```

## Endpoint Tests

### `GET /users`

- Status: `tested`
- Tested path: `/users`
- HTTP: `405 Method Not Allowed`
- Elapsed: `268 ms`
- Content-Type: `application/json`
- Allow: `POST, OPTIONS`

#### Tested Response Shape

```json
{
  "detail": "str"
}
```

## API refresh 2026-09-22

Users collection. / Discovered from platform frontend bundle.

- Advertised methods: GET, OPTIONS, POST.
- Live OPTIONS status: 200. Mutation methods were not executed.
- Account-specific option values are omitted; use `wqb api call` with OPTIONS for current metadata.
