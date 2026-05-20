# `/captcha`

- URL template: `https://api.worldquantbrain.com/captcha`
- Methods: `GET`
- Sources: `platform_dynamic_capture`
- Safe probe: `True`
- Description: Observed by passive platform network capture.

## Probe

- Skipped/Error: `Observed by platform dynamic network capture; no separate safe probe was run.`

## Dynamic Capture

### `GET /captcha`

- Seen count: `14`
- Status codes: `200`
- Query keys: ``
- Content types: `application/json`

#### Response Shape

```json
{
  "algorithm": "str",
  "challenge": "str",
  "maxNumber": "int",
  "salt": "str",
  "signature": "str"
}
```

## Endpoint Tests

### `GET /captcha`

- Status: `tested`
- Tested path: `/captcha`
- HTTP: `200 OK`
- Elapsed: `270 ms`
- Content-Type: `application/json`
- Allow: `GET, POST, HEAD, OPTIONS`

#### Tested Response Shape

```json
{
  "algorithm": "str",
  "challenge": "str",
  "maxNumber": "int",
  "salt": "str",
  "signature": "str"
}
```
