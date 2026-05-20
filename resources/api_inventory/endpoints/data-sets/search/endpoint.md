# `/data-sets/search`

- URL template: `https://api.worldquantbrain.com/data-sets/search`
- Methods: `GET, POST`
- Sources: `platform_frontend`
- Safe probe: `True`
- Description: Dataset search helper. / Discovered from platform frontend bundle.

## Probe

- Probe URL: `https://api.worldquantbrain.com/data-sets/search`
- Allowed methods: `GET, HEAD, OPTIONS`
- Status: `400 Bad Request`
- Usable GET: `False`

### Response Shape

```json
{
  "detail": "str"
}
```

## Endpoint Tests

### `GET /data-sets/search`

- Status: `tested`
- Tested path: `/data-sets/search`
- HTTP: `400 Bad Request`
- Elapsed: `259 ms`
- Content-Type: `application/json`
- Allow: `GET, HEAD, OPTIONS`

#### Tested Response Shape

```json
{
  "detail": "str"
}
```
### `POST /data-sets/search`

- Status: `skipped_mutating`
- Tested path: `/data-sets/search`
- Reason: POST may mutate remote state; not executed by inventory test.
