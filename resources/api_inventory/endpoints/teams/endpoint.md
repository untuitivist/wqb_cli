# `/teams`

- URL template: `https://api.worldquantbrain.com/teams`
- Methods: `GET`
- Sources: `platform_frontend`
- Safe probe: `True`
- Description: Teams. / Discovered from platform frontend bundle.

## Probe

- Probe URL: `https://api.worldquantbrain.com/teams`
- Allowed methods: `POST, OPTIONS`
- Status: `405 Method Not Allowed`
- Usable GET: `False`

### Response Shape

```json
{
  "detail": "str"
}
```

## Endpoint Tests

### `GET /teams`

- Status: `tested`
- Tested path: `/teams`
- HTTP: `405 Method Not Allowed`
- Elapsed: `260 ms`
- Content-Type: `application/json`
- Allow: `POST, OPTIONS`

#### Tested Response Shape

```json
{
  "detail": "str"
}
```
