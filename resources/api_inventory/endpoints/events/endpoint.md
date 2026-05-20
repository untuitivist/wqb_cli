# `/events`

- URL template: `https://api.worldquantbrain.com/events`
- Methods: `GET, OPTIONS`
- Sources: `observed_platform, platform_dynamic_capture, platform_frontend`
- Safe probe: `True`
- Description: Events list. / Discovered from platform frontend bundle.
- Params: `{"limit": "optional", "offset": "optional", "order": "observed query parameter", "start>": "observed query parameter"}`

## Probe

- Probe URL: `https://api.worldquantbrain.com/events?limit=1`
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
      "title": "str",
      "type": "str",
      "category": "NoneType",
      "start": "str",
      "end": "str",
      "timezone": "str",
      "language": "str",
      "description": "str",
      "register": "str",
      "venue": "NoneType",
      "city": "NoneType",
      "country": "str"
    }
  ]
}
```

## Dynamic Capture

### `GET /events`

- Seen count: `2`
- Status codes: `200`
- Query keys: `limit, order, start>`
- Content types: `application/json`

#### Response Shape

```json
{
  "count": "int",
  "next": "null",
  "previous": "null",
  "results": [
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
  ]
}
```
### `OPTIONS /events`

- Seen count: `1`
- Status codes: `200`
- Query keys: ``
- Content types: `application/json`

#### Response Shape

```json
{
  "actions": {
    "GET": {
      "category": {
        "choices": "list",
        "label": "str",
        "readOnly": "bool",
        "required": "bool",
        "type": "str"
      },
      "city": {
        "choices": "list",
        "label": "str",
        "readOnly": "bool",
        "required": "bool",
        "type": "str"
      },
      "country": {
        "choices": "list",
        "label": "str",
        "readOnly": "bool",
        "required": "bool",
        "type": "str"
      },
      "description": {
        "label": "str",
        "maxLength": "int",
        "readOnly": "bool",
        "required": "bool",
        "type": "str"
      },
      "end": {
        "label": "str",
        "readOnly": "bool",
        "required": "bool",
        "type": "str"
      },
      "id": {
        "label": "str",
        "readOnly": "bool",
        "required": "bool",
        "type": "str"
      },
      "language": {
        "choices": "list",
        "label": "str",
        "readOnly": "bool",
        "required": "bool",
        "type": "str"
      },
      "register": {
        "label": "str",
        "readOnly": "bool",
        "required": "bool",
        "type": "str"
      },
      "start": {
        "label": "str",
        "readOnly": "bool",
        "required": "bool",
        "type": "str"
      },
      "timezone": {
        "label": "str",
        "readOnly": "bool",
        "required": "bool",
        "type": "str"
      },
      "title": {
        "label": "str",
        "maxLength": "int",
        "readOnly": "bool",
        "required": "bool",
        "type": "str"
      },
      "type": {
        "label": "str",
        "readOnly": "bool",
        "required": "bool",
        "type": "str"
      },
      "venue": {
        "label": "str",
        "maxLength": "int",
        "readOnly": "bool",
        "required": "bool",
        "type": "str"
      }
    }
  }
}
```

## Endpoint Tests

### `GET /events`

- Status: `tested`
- Tested path: `/events`
- HTTP: `200 OK`
- Elapsed: `267 ms`
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
  ]
}
```
### `OPTIONS /events`

- Status: `tested`
- Tested path: `/events`
- HTTP: `200 OK`
- Elapsed: `264 ms`
- Content-Type: `application/json`
- Allow: `GET, HEAD, OPTIONS`

#### Tested Response Shape

```json
{
  "actions": {
    "GET": {
      "category": {
        "choices": "list",
        "label": "str",
        "readOnly": "bool",
        "required": "bool",
        "type": "str"
      },
      "city": {
        "choices": "list",
        "label": "str",
        "readOnly": "bool",
        "required": "bool",
        "type": "str"
      },
      "country": {
        "choices": "list",
        "label": "str",
        "readOnly": "bool",
        "required": "bool",
        "type": "str"
      },
      "description": {
        "label": "str",
        "maxLength": "int",
        "readOnly": "bool",
        "required": "bool",
        "type": "str"
      },
      "end": {
        "label": "str",
        "readOnly": "bool",
        "required": "bool",
        "type": "str"
      },
      "id": {
        "label": "str",
        "readOnly": "bool",
        "required": "bool",
        "type": "str"
      },
      "language": {
        "choices": "list",
        "label": "str",
        "readOnly": "bool",
        "required": "bool",
        "type": "str"
      },
      "register": {
        "label": "str",
        "readOnly": "bool",
        "required": "bool",
        "type": "str"
      },
      "start": {
        "label": "str",
        "readOnly": "bool",
        "required": "bool",
        "type": "str"
      },
      "timezone": {
        "label": "str",
        "readOnly": "bool",
        "required": "bool",
        "type": "str"
      },
      "title": {
        "label": "str",
        "maxLength": "int",
        "readOnly": "bool",
        "required": "bool",
        "type": "str"
      },
      "type": {
        "label": "str",
        "readOnly": "bool",
        "required": "bool",
        "type": "str"
      },
      "venue": {
        "label": "str",
        "maxLength": "int",
        "readOnly": "bool",
        "required": "bool",
        "type": "str"
      }
    }
  }
}
```
