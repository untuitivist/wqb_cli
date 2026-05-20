# `/user/password/reset`

- URL template: `https://api.worldquantbrain.com/user/password/reset`
- Methods: `GET, POST`
- Sources: `platform_frontend`
- Safe probe: `False`
- Description: Reset password. / Discovered from platform frontend bundle.
- Request body: Account mutation.

## Probe

- Skipped

## Endpoint Tests

### `GET /user/password/reset`

- Status: `tested`
- Tested path: `/user/password/reset`
- HTTP: `405 Method Not Allowed`
- Elapsed: `258 ms`
- Content-Type: `application/json`
- Allow: `POST, OPTIONS`

#### Tested Response Shape

```json
{
  "detail": "str"
}
```
### `POST /user/password/reset`

- Status: `skipped_mutating`
- Tested path: `/user/password/reset`
- Reason: POST may mutate remote state; not executed by inventory test.
