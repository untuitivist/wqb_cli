# `/events/{event_id}`

- URL template: `https://api.worldquantbrain.com/events/{event_id}`
- Methods: `GET`
- Sources: `platform_frontend`
- Safe probe: `False`
- Description: Event details. / Discovered from platform frontend bundle.

## Probe

- Skipped

## Endpoint Tests

### `GET /events/{event_id}`

- Status: `tested`
- Tested path: `/events/zO8y3jm`
- HTTP: `200 OK`
- Elapsed: `313 ms`
- Content-Type: `application/json`
- Allow: `GET, HEAD, OPTIONS`

#### Tested Response Shape

```json
{
  "category": "null",
  "city": "null",
  "country": "str",
  "description": "str",
  "end": "str",
  "id": "str",
  "language": "str",
  "register": "str",
  "start": "str",
  "timezone": "str",
  "title": "str",
  "type": "str",
  "venue": "null"
}
```
