# `/configuration`

- URL template: `https://api.worldquantbrain.com/configuration`
- Methods: `GET`
- Sources: `platform_dynamic_capture, platform_frontend`
- Safe probe: `True`
- Description: Platform configuration. / Discovered from platform frontend bundle.

## Probe

- Probe URL: `https://api.worldquantbrain.com/configuration`
- Allowed methods: `GET, HEAD, OPTIONS`
- Status: `200 OK`
- Usable GET: `True`

### Response Shape

```json
{
  "analytics": {
    "trackingId": "NoneType"
  },
  "recaptcha": {
    "siteKey": "str"
  },
  "recaptchaV3": {
    "siteKey": "str"
  }
}
```

## Dynamic Capture

### `GET /configuration`

- Seen count: `14`
- Status codes: `200`
- Query keys: ``
- Content types: `application/json`

#### Response Shape

```json
{
  "analytics": {
    "trackingId": "null"
  },
  "recaptcha": {
    "siteKey": "str"
  },
  "recaptchaV3": {
    "siteKey": "str"
  }
}
```

## Endpoint Tests

### `GET /configuration`

- Status: `tested`
- Tested path: `/configuration`
- HTTP: `200 OK`
- Elapsed: `253 ms`
- Content-Type: `application/json`
- Allow: `GET, HEAD, OPTIONS`

#### Tested Response Shape

```json
{
  "analytics": {
    "trackingId": "null"
  },
  "recaptcha": {
    "siteKey": "str"
  },
  "recaptchaV3": {
    "siteKey": "str"
  }
}
```
