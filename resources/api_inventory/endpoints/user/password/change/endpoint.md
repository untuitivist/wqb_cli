# `/user/password/change`

- URL template: `https://api.worldquantbrain.com/user/password/change`
- Methods: `GET, POST`
- Sources: `platform_frontend`
- Safe probe: `False`
- Description: Change password. / Discovered from platform frontend bundle.
- Request body: Account mutation.

## Probe

- Skipped

## Endpoint Tests

### `GET /user/password/change`

- Status: `tested`
- Tested path: `/user/password/change`
- HTTP: `405 Method Not Allowed`
- Elapsed: `265 ms`
- Content-Type: `application/json`
- Allow: `POST, OPTIONS`

#### Tested Response Shape

```json
{
  "detail": "str"
}
```
### `POST /user/password/change`

- Status: `skipped_mutating`
- Tested path: `/user/password/change`
- Reason: POST may mutate remote state; not executed by inventory test.

## API refresh 2026-09-22

Change password. / Discovered from platform frontend bundle.

- Advertised methods: GET, OPTIONS, POST.
- Live OPTIONS status: 200. Mutation methods were not executed.
- Account-specific option values are omitted; use `wqb api call` with OPTIONS for current metadata.
