# `/user/email/verify`

- URL template: `https://api.worldquantbrain.com/user/email/verify`
- Methods: `GET, POST`
- Sources: `platform_frontend`
- Safe probe: `False`
- Description: Verify email. / Discovered from platform frontend bundle.
- Request body: Account mutation.

## Probe

- Skipped

## Endpoint Tests

### `GET /user/email/verify`

- Status: `tested`
- Tested path: `/user/email/verify`
- HTTP: `405 Method Not Allowed`
- Elapsed: `259 ms`
- Content-Type: `application/json`
- Allow: `POST, OPTIONS`

#### Tested Response Shape

```json
{
  "detail": "str"
}
```
### `POST /user/email/verify`

- Status: `skipped_mutating`
- Tested path: `/user/email/verify`
- Reason: POST may mutate remote state; not executed by inventory test.

## API refresh 2026-09-22

Verify email. / Discovered from platform frontend bundle.

- Advertised methods: GET, OPTIONS, POST.
- Live OPTIONS status: 200. Mutation methods were not executed.
- Account-specific option values are omitted; use `wqb api call` with OPTIONS for current metadata.
