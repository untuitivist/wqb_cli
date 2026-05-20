# `/user/token`

- URL template: `https://api.worldquantbrain.com/user/token`
- Methods: `GET, POST`
- Sources: `platform_frontend`
- Safe probe: `False`
- Description: User token endpoint. / Discovered from platform frontend bundle.
- Request body: Token operation.

## Probe

- Skipped

## Endpoint Tests

### `GET /user/token`

- Status: `tested`
- Tested path: `/user/token`
- HTTP: `405 Method Not Allowed`
- Elapsed: `262 ms`
- Content-Type: `application/json`
- Allow: `POST, OPTIONS`

#### Tested Response Shape

```json
{
  "detail": "str"
}
```
### `POST /user/token`

- Status: `skipped_mutating`
- Tested path: `/user/token`
- Reason: POST may mutate remote state; not executed by inventory test.
