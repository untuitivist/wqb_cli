# `/suggest/expression`

- URL template: `https://api.worldquantbrain.com/suggest/expression`
- Methods: `GET, POST`
- Sources: `platform_frontend`
- Safe probe: `True`
- Description: Expression suggestion. / Discovered from platform frontend bundle.
- Request body: POST may send prompt/context.

## Probe

- Probe URL: `https://api.worldquantbrain.com/suggest/expression`
- Status: `404 Not Found`
- Usable GET: `False`

### Response Shape

```json
{
  "detail": "str"
}
```

## Endpoint Tests

### `GET /suggest/expression`

- Status: `tested`
- Tested path: `/suggest/expression`
- HTTP: `404 Not Found`
- Elapsed: `257 ms`
- Content-Type: `application/json`

#### Tested Response Shape

```json
{
  "detail": "str"
}
```
### `POST /suggest/expression`

- Status: `skipped_mutating`
- Tested path: `/suggest/expression`
- Reason: POST may mutate remote state; not executed by inventory test.
