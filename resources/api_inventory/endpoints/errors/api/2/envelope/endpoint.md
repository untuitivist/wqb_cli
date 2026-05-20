# `/errors/api/2/envelope`

- URL template: `https://api.worldquantbrain.com/errors/api/2/envelope`
- Methods: `POST`
- Sources: `platform_dynamic_capture`
- Safe probe: `False`
- Description: Observed by passive platform network capture.
- Params: `{"sentry_client": "observed query parameter", "sentry_key": "observed query parameter", "sentry_version": "observed query parameter"}`
- Request body: Observed request body shape in dynamic_capture.

## Probe

- Skipped/Error: `Observed by platform dynamic network capture; no separate safe probe was run.`

## Dynamic Capture

### `POST /errors/api/2/envelope/`

- Seen count: `61`
- Status codes: `200`
- Query keys: `sentry_client, sentry_key, sentry_version`
- Content types: `application/json`

#### Request Body Shape

```json
{
  "raw_body": "non-json",
  "length": 463
}
```

#### Response Shape

```json
{}
```

## Endpoint Tests

### `POST /errors/api/2/envelope`

- Status: `skipped_mutating`
- Tested path: `/errors/api/2/envelope`
- Reason: POST may mutate remote state; not executed by inventory test.
