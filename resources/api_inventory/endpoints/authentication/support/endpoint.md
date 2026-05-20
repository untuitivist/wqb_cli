# `/authentication/support`

- URL template: `https://api.worldquantbrain.com/authentication/support`
- Methods: `GET`
- Sources: `platform_frontend`
- Safe probe: `True`
- Description: Discovered from platform frontend bundle.
- Params: `{"query": "return_to="}`

## Probe

- Probe URL: `https://api.worldquantbrain.com/authentication/support`
- Allowed methods: `GET, HEAD, OPTIONS`
- Status: `403 Forbidden`
- Usable GET: `False`

### Response Shape

```json
"text"
```

## Endpoint Tests

### `GET /authentication/support`

- Status: `tested`
- Tested path: `/authentication/support`
- HTTP: `302 Found`
- Elapsed: `1511 ms`
- Allow: `GET, HEAD, OPTIONS`
