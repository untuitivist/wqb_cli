# `/user/email/change`

- URL template: `https://api.worldquantbrain.com/user/email/change`
- Methods: `GET, POST`
- Sources: `platform_frontend`
- Safe probe: `False`
- Description: Change email. / Discovered from platform frontend bundle.
- Request body: Account mutation.

## Probe

- Skipped

## Endpoint Tests

### `GET /user/email/change`

- Status: `tested`
- Tested path: `/user/email/change`
- HTTP: `405 Method Not Allowed`
- Elapsed: `257 ms`
- Content-Type: `application/json`
- Allow: `POST, OPTIONS`

#### Tested Response Shape

```json
{
  "detail": "str"
}
```
### `POST /user/email/change`

- Status: `skipped_mutating`
- Tested path: `/user/email/change`
- Reason: POST may mutate remote state; not executed by inventory test.
