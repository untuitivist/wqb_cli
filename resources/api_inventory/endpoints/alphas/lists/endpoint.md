# `/alphas/lists`

- URL template: `https://api.worldquantbrain.com/alphas/lists`
- Methods: `GET`
- Sources: `platform_frontend`
- Safe probe: `True`
- Description: Alpha lists. / Discovered from platform frontend bundle.

## Probe

- Probe URL: `https://api.worldquantbrain.com/alphas/lists`
- Allowed methods: `GET, PUT, PATCH, HEAD, OPTIONS`
- Status: `404 Not Found`
- Usable GET: `False`

### Response Shape

```json
{
  "detail": "str"
}
```

## Endpoint Tests

### `GET /alphas/lists`

- Status: `tested`
- Tested path: `/alphas/lists`
- HTTP: `404 Not Found`
- Elapsed: `286 ms`
- Content-Type: `application/json`
- Allow: `GET, PUT, PATCH, HEAD, OPTIONS`

#### Tested Response Shape

```json
{
  "detail": "str"
}
```
