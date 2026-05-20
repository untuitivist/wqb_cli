# `/users/self/messages`

- URL template: `https://api.worldquantbrain.com/users/self/messages`
- Methods: `GET`
- Sources: `observed_platform, platform_dynamic_capture`
- Safe probe: `True`
- Description: Current user's messages.
- Params: `{"limit": "optional", "offset": "optional", "order": "observed query parameter", "type": "observed query parameter"}`

## Probe

- Probe URL: `https://api.worldquantbrain.com/users/self/messages`
- Allowed methods: `GET, HEAD, OPTIONS`
- Status: `200 OK`
- Usable GET: `True`

### Response Shape

```json
{
  "count": "int",
  "next": "str",
  "previous": "NoneType",
  "results": [
    {
      "id": "str",
      "type": "str",
      "title": "str",
      "description": "str",
      "dateCreated": "str",
      "tags": [],
      "read": "bool"
    }
  ]
}
```

## Dynamic Capture

### `GET /users/self/messages`

- Seen count: `16`
- Status codes: `200`
- Query keys: `limit, order, type`
- Content types: `application/json`

#### Response Shape

```json
{
  "count": "int",
  "next": "str",
  "previous": "null",
  "results": [
    {
      "dateCreated": "str",
      "description": "str",
      "id": "str",
      "read": "bool",
      "tags": [],
      "title": "str",
      "type": "str"
    }
  ]
}
```

## Endpoint Tests

### `GET /users/self/messages`

- Status: `tested`
- Tested path: `/users/self/messages`
- HTTP: `200 OK`
- Elapsed: `500 ms`
- Content-Type: `application/json`
- Allow: `GET, HEAD, OPTIONS`

#### Tested Response Shape

```json
{
  "count": "int",
  "next": "str",
  "previous": "null",
  "results": [
    {
      "dateCreated": "str",
      "description": "str",
      "id": "str",
      "read": "bool",
      "tags": [],
      "title": "str",
      "type": "str"
    }
  ]
}
```
