# `/tutorial/{tutorial_slug}`

- URL template: `https://api.worldquantbrain.com/tutorial/{tutorial_slug}`
- Methods: `GET`
- Sources: `platform_dynamic_capture`
- Safe probe: `True`
- Description: Observed by passive platform network capture.

## Probe

- Skipped/Error: `Observed by platform dynamic network capture; no separate safe probe was run.`

## Dynamic Capture

### `GET /tutorial/exclusive-events-and-support-for-consultants`

- Seen count: `8`
- Status codes: `200`
- Query keys: ``
- Content types: `application/json`

#### Response Shape

```json
{
  "category": "str",
  "content": [
    {
      "id": "str",
      "type": "str",
      "value": {
        "content": "str",
        "level": "str"
      }
    }
  ],
  "id": "str",
  "lastModified": "str",
  "sequence": "int",
  "title": "str"
}
```

## Endpoint Tests

### `GET /tutorial/{tutorial_slug}`

- Status: `tested`
- Tested path: `/tutorial/exclusive-events-and-support-for-consultants`
- HTTP: `200 OK`
- Elapsed: `289 ms`
- Content-Type: `application/json`
- Allow: `GET, HEAD, OPTIONS`

#### Tested Response Shape

```json
{
  "category": "str",
  "content": [
    {
      "id": "str",
      "type": "str",
      "value": {
        "content": "str",
        "level": "str"
      }
    }
  ],
  "id": "str",
  "lastModified": "str",
  "sequence": "int",
  "title": "str"
}
```
