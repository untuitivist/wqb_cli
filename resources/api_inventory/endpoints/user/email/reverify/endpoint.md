# `/user/email/reverify`

- URL template: `https://api.worldquantbrain.com/user/email/reverify`
- Methods: `GET, POST`
- Sources: `platform_frontend`
- Safe probe: `False`
- Description: Reverify email. / Discovered from platform frontend bundle.
- Request body: Account mutation.

## Probe

- Skipped

## Endpoint Tests

### `GET /user/email/reverify`

- Status: `tested`
- Tested path: `/user/email/reverify`
- HTTP: `405 Method Not Allowed`
- Elapsed: `261 ms`
- Content-Type: `application/json`
- Allow: `POST, OPTIONS`

#### Tested Response Shape

```json
{
  "detail": "str"
}
```
### `POST /user/email/reverify`

- Status: `skipped_mutating`
- Tested path: `/user/email/reverify`
- Reason: POST may mutate remote state; not executed by inventory test.
