# `/consultant`

- URL template: `https://api.worldquantbrain.com/consultant`
- Methods: `GET`
- Sources: `platform_frontend`
- Safe probe: `True`
- Description: Consultant landing endpoint. / Discovered from platform frontend bundle.

## Probe

- Probe URL: `https://api.worldquantbrain.com/consultant`
- Status: `404 Not Found`
- Usable GET: `False`

### Response Shape

```json
{
  "detail": "str"
}
```

## Endpoint Tests

### `GET /consultant`

- Status: `tested`
- Tested path: `/consultant`
- HTTP: `404 Not Found`
- Elapsed: `267 ms`
- Content-Type: `application/json`

#### Tested Response Shape

```json
{
  "detail": "str"
}
```
