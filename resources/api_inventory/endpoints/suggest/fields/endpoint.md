# `/suggest/fields`

- URL template: `https://api.worldquantbrain.com/suggest/fields`
- Methods: `GET, POST`
- Sources: `platform_dynamic_capture, platform_frontend`
- Safe probe: `True`
- Description: Field suggestion. / Discovered from platform frontend bundle.
- Request body: POST may send prompt/context.

## Probe

- Probe URL: `https://api.worldquantbrain.com/suggest/fields`
- Allowed methods: `GET, HEAD, OPTIONS`
- Status: `200 OK`
- Usable GET: `True`

### Response Shape

```json
{
  "selection": [
    "str"
  ],
  "combo": [
    "str"
  ]
}
```

## Dynamic Capture

### `GET /suggest/fields`

- Seen count: `8`
- Status codes: `200`
- Query keys: ``
- Content types: `application/json`

#### Response Shape

```json
{
  "combo": [
    "str"
  ],
  "selection": [
    "str"
  ]
}
```

## Endpoint Tests

### `GET /suggest/fields`

- Status: `tested`
- Tested path: `/suggest/fields`
- HTTP: `200 OK`
- Elapsed: `314 ms`
- Content-Type: `application/json`
- Allow: `GET, HEAD, OPTIONS`

#### Tested Response Shape

```json
{
  "combo": [
    "str"
  ],
  "selection": [
    "str"
  ]
}
```
### `POST /suggest/fields`

- Status: `skipped_mutating`
- Tested path: `/suggest/fields`
- Reason: POST may mutate remote state; not executed by inventory test.
