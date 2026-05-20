# `/alphas/distribution`

- URL template: `https://api.worldquantbrain.com/alphas/distribution`
- Methods: `GET`
- Sources: `platform_frontend`
- Safe probe: `True`
- Description: Alpha distribution aggregate. / Discovered from platform frontend bundle.

## Probe

- Probe URL: `https://api.worldquantbrain.com/alphas/distribution`
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

### `GET /alphas/distribution`

- Status: `tested`
- Tested path: `/alphas/distribution`
- HTTP: `404 Not Found`
- Elapsed: `271 ms`
- Content-Type: `application/json`
- Allow: `GET, PUT, PATCH, HEAD, OPTIONS`

#### Tested Response Shape

```json
{
  "detail": "str"
}
```
