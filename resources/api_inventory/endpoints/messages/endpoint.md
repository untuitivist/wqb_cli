# `/messages`

- URL template: `https://api.worldquantbrain.com/messages`
- Methods: `GET`
- Sources: `platform_frontend`
- Safe probe: `True`
- Description: Message collection. / Discovered from platform frontend bundle.

## Probe

- Probe URL: `https://api.worldquantbrain.com/messages`
- Status: `404 Not Found`
- Usable GET: `False`

### Response Shape

```json
{
  "detail": "str"
}
```

## Endpoint Tests

### `GET /messages`

- Status: `tested`
- Tested path: `/messages`
- HTTP: `404 Not Found`
- Elapsed: `260 ms`
- Content-Type: `application/json`

#### Tested Response Shape

```json
{
  "detail": "str"
}
```
