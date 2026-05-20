# `/users/self/messages/summary`

- URL template: `https://api.worldquantbrain.com/users/self/messages/summary`
- Methods: `GET`
- Sources: `platform_dynamic_capture`
- Safe probe: `True`
- Description: Observed by passive platform network capture.

## Probe

- Skipped/Error: `Observed by platform dynamic network capture; no separate safe probe was run.`

## Dynamic Capture

### `GET /users/self/messages/summary`

- Seen count: `14`
- Status codes: `200`
- Query keys: ``
- Content types: `application/json`

#### Response Shape

```json
{
  "announcement": {
    "count": "int",
    "read": "int",
    "unread": "int"
  },
  "notification": {
    "count": "int",
    "read": "int",
    "unread": "int"
  }
}
```

## Endpoint Tests

### `GET /users/self/messages/summary`

- Status: `tested`
- Tested path: `/users/self/messages/summary`
- HTTP: `200 OK`
- Elapsed: `263 ms`
- Content-Type: `application/json`
- Allow: `GET, PATCH, HEAD, OPTIONS`

#### Tested Response Shape

```json
{
  "announcement": {
    "count": "int",
    "read": "int",
    "unread": "int"
  },
  "notification": {
    "count": "int",
    "read": "int",
    "unread": "int"
  }
}
```
