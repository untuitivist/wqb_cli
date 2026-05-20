# `/alphas`

- URL template: `https://api.worldquantbrain.com/alphas`
- Methods: `GET`
- Sources: `platform_frontend, rocky-d/wqb`
- Safe probe: `True`
- Description: Alpha collection. / Discovered from platform frontend bundle.
- Params: `{"limit": "1..100", "offset": "0..10000", "query": "limit=5"}`

## Probe

- Probe URL: `https://api.worldquantbrain.com/alphas?limit=1`
- Allowed methods: `POST, PUT, PATCH, OPTIONS`
- Status: `405 Method Not Allowed`
- Usable GET: `False`

### Response Shape

```json
{
  "detail": "str"
}
```

## Endpoint Tests

### `GET /alphas`

- Status: `tested`
- Tested path: `/alphas`
- HTTP: `405 Method Not Allowed`
- Elapsed: `270 ms`
- Content-Type: `application/json`
- Allow: `POST, PUT, PATCH, OPTIONS`

#### Tested Response Shape

```json
{
  "detail": "str"
}
```
