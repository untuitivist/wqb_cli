# `/alphas/{alpha_id}/alphas`

- URL template: `https://api.worldquantbrain.com/alphas/{alpha_id}/alphas`
- Methods: `GET`
- Sources: `platform_frontend`
- Safe probe: `True`
- Description: Discovered from platform frontend bundle.

## Probe

- Probe URL: `https://api.worldquantbrain.com/alphas/vR5p8vqb/alphas`
- Allowed methods: `GET, HEAD, OPTIONS`
- Status: `404 Not Found`
- Usable GET: `False`

### Response Shape

```json
{
  "detail": "str"
}
```

## Endpoint Tests

### `GET /alphas/{alpha_id}/alphas`

- Status: `tested`
- Tested path: `/alphas/vR5p8vqb/alphas`
- HTTP: `404 Not Found`
- Elapsed: `265 ms`
- Content-Type: `application/json`
- Allow: `GET, HEAD, OPTIONS`

#### Tested Response Shape

```json
{
  "detail": "str"
}
```
