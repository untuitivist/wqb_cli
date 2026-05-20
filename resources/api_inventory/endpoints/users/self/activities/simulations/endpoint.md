# `/users/self/activities/simulations`

- URL template: `https://api.worldquantbrain.com/users/self/activities/simulations`
- Methods: `GET`
- Sources: `platform_dynamic_capture`
- Safe probe: `True`
- Description: Observed by passive platform network capture.
- Params: `{"date>": "observed query parameter"}`

## Probe

- Skipped/Error: `Observed by platform dynamic network capture; no separate safe probe was run.`

## Dynamic Capture

### `GET /users/self/activities/simulations`

- Seen count: `8`
- Status codes: `200`
- Query keys: `date>`
- Content types: `application/json`

#### Response Shape

```json
{
  "current": {
    "end": "str",
    "start": "str",
    "value": "int"
  },
  "previous": {
    "end": "str",
    "start": "str",
    "value": "int"
  },
  "records": {
    "records": [
      [
        "str"
      ]
    ],
    "schema": {
      "name": "str",
      "properties": [
        "dict"
      ],
      "title": "str"
    }
  },
  "total": {
    "end": "str",
    "start": "str",
    "value": "int"
  },
  "type": "str",
  "yesterday": {
    "end": "str",
    "start": "str",
    "value": "int"
  },
  "ytd": {
    "end": "str",
    "start": "str",
    "value": "int"
  }
}
```

## Endpoint Tests

### `GET /users/self/activities/simulations`

- Status: `tested`
- Tested path: `/users/self/activities/simulations`
- HTTP: `200 OK`
- Elapsed: `268 ms`
- Content-Type: `application/json`
- Allow: `GET, HEAD, OPTIONS`

#### Tested Response Shape

```json
{
  "current": {
    "end": "str",
    "start": "str",
    "value": "int"
  },
  "previous": {
    "end": "str",
    "start": "str",
    "value": "int"
  },
  "records": {
    "records": [
      [
        "str"
      ]
    ],
    "schema": {
      "name": "str",
      "properties": [
        "dict"
      ],
      "title": "str"
    }
  },
  "total": {
    "end": "str",
    "start": "str",
    "value": "int"
  },
  "type": "str",
  "yesterday": {
    "end": "str",
    "start": "str",
    "value": "int"
  },
  "ytd": {
    "end": "str",
    "start": "str",
    "value": "int"
  }
}
```
