# `/user/password/forgot`

- URL template: `https://api.worldquantbrain.com/user/password/forgot`
- Methods: `GET, POST`
- Sources: `platform_frontend`
- Safe probe: `False`
- Description: Forgot password. / Discovered from platform frontend bundle.
- Request body: Account mutation.

## Probe

- Skipped

## Endpoint Tests

### `GET /user/password/forgot`

- Status: `tested`
- Tested path: `/user/password/forgot`
- HTTP: `405 Method Not Allowed`
- Elapsed: `264 ms`
- Content-Type: `application/json`
- Allow: `POST, OPTIONS`

#### Tested Response Shape

```json
{
  "detail": "str"
}
```
### `POST /user/password/forgot`

- Status: `skipped_mutating`
- Tested path: `/user/password/forgot`
- Reason: POST may mutate remote state; not executed by inventory test.
