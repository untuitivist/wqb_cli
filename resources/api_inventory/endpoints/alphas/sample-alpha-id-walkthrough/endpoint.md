# `/alphas/sample-alpha-id-walkthrough`

- URL template: `https://api.worldquantbrain.com/alphas/sample-alpha-id-walkthrough`
- Methods: `GET`
- Sources: `platform_frontend`
- Safe probe: `True`
- Description: Discovered from platform frontend bundle.

## Probe

- Probe URL: `https://api.worldquantbrain.com/alphas/sample-alpha-id-walkthrough`
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

### `GET /alphas/sample-alpha-id-walkthrough`

- Status: `tested`
- Tested path: `/alphas/sample-alpha-id-walkthrough`
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
