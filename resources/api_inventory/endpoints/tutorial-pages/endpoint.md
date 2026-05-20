# `/tutorial-pages`

- URL template: `https://api.worldquantbrain.com/tutorial-pages`
- Methods: `GET`
- Sources: `platform_frontend`
- Safe probe: `True`
- Description: Tutorial pages. / Discovered from platform frontend bundle.

## Probe

- Probe URL: `https://api.worldquantbrain.com/tutorial-pages`
- Allowed methods: `GET, HEAD, OPTIONS`
- Status: `404 Not Found`
- Usable GET: `False`

### Response Shape

```json
{
  "message": "str"
}
```

## Endpoint Tests

### `GET /tutorial-pages`

- Status: `tested`
- Tested path: `/tutorial-pages`
- HTTP: `404 Not Found`
- Elapsed: `255 ms`
- Content-Type: `application/json`
- Allow: `GET, HEAD, OPTIONS`

#### Tested Response Shape

```json
{
  "message": "str"
}
```
