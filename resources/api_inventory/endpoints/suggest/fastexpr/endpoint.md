# `/suggest/fastexpr`

- URL template: `https://api.worldquantbrain.com/suggest/fastexpr`
- Methods: `GET, POST`
- Sources: `platform_frontend`
- Safe probe: `True`
- Description: FastExpr suggestion. / Discovered from platform frontend bundle.
- Request body: POST may send prompt/context.

## Probe

- Probe URL: `https://api.worldquantbrain.com/suggest/fastexpr`
- Status: `404 Not Found`
- Usable GET: `False`

### Response Shape

```json
{
  "detail": "str"
}
```

## Endpoint Tests

### `GET /suggest/fastexpr`

- Status: `tested`
- Tested path: `/suggest/fastexpr`
- HTTP: `404 Not Found`
- Elapsed: `282 ms`
- Content-Type: `application/json`

#### Tested Response Shape

```json
{
  "detail": "str"
}
```
### `POST /suggest/fastexpr`

- Status: `skipped_mutating`
- Tested path: `/suggest/fastexpr`
- Reason: POST may mutate remote state; not executed by inventory test.
