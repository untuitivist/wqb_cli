# `/consultant-program/{language}`

- URL template: `https://api.worldquantbrain.com/consultant-program/{language}`
- Methods: `GET`
- Sources: `platform_frontend`
- Safe probe: `False`
- Description: Consultant program by language. / Discovered from platform frontend bundle.

## Probe

- Skipped

## Endpoint Tests

### `GET /consultant-program/{language}`

- Status: `tested`
- Tested path: `/consultant-program/en`
- HTTP: `404 Not Found`
- Elapsed: `255 ms`
- Content-Type: `application/json`

#### Tested Response Shape

```json
{
  "detail": "str"
}
```
