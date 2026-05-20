# `/alphas/super-selection`

- URL template: `https://api.worldquantbrain.com/alphas/super-selection`
- Methods: `GET`
- Sources: `platform_frontend`
- Safe probe: `True`
- Description: Super selection alpha endpoint. / Discovered from platform frontend bundle.

## Probe

- Probe URL: `https://api.worldquantbrain.com/alphas/super-selection`
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

### `GET /alphas/super-selection`

- Status: `tested`
- Tested path: `/alphas/super-selection`
- HTTP: `404 Not Found`
- Elapsed: `290 ms`
- Content-Type: `application/json`
- Allow: `GET, PUT, PATCH, HEAD, OPTIONS`

#### Tested Response Shape

```json
{
  "detail": "str"
}
```
