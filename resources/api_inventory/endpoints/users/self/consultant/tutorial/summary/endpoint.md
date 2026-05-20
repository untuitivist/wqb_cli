# `/users/self/consultant/tutorial/summary`

- URL template: `https://api.worldquantbrain.com/users/self/consultant/tutorial/summary`
- Methods: `GET, PATCH`
- Sources: `platform_dynamic_capture`
- Safe probe: `False`
- Description: Observed by passive platform network capture.
- Request body: Observed request body shape in dynamic_capture.

## Probe

- Skipped/Error: `Observed by platform dynamic network capture; no separate safe probe was run.`

## Dynamic Capture

### `GET /users/self/consultant/tutorial/summary`

- Seen count: `22`
- Status codes: `200`
- Query keys: ``
- Content types: `application/json`

#### Response Shape

```json
{
  "active": "bool",
  "currentStep": "int",
  "status": "str",
  "steps": [
    {
      "answer": "null",
      "hint": "null",
      "id": "int",
      "name": "str",
      "requirements": "null",
      "slug": "str",
      "status": "str",
      "task": "null",
      "visited": "bool"
    }
  ]
}
```
### `PATCH /users/self/consultant/tutorial/summary`

- Seen count: `8`
- Status codes: `200`
- Query keys: ``
- Content types: `text/html`

#### Request Body Shape

```json
{
  "active": "bool"
}
```

## Endpoint Tests

### `GET /users/self/consultant/tutorial/summary`

- Status: `tested`
- Tested path: `/users/self/consultant/tutorial/summary`
- HTTP: `200 OK`
- Elapsed: `302 ms`
- Content-Type: `application/json`
- Allow: `GET, PATCH, HEAD, OPTIONS`

#### Tested Response Shape

```json
{
  "active": "bool",
  "currentStep": "int",
  "status": "str",
  "steps": [
    {
      "answer": "null",
      "hint": "null",
      "id": "int",
      "name": "str",
      "requirements": "null",
      "slug": "str",
      "status": "str",
      "task": "null",
      "visited": "bool"
    }
  ]
}
```
### `PATCH /users/self/consultant/tutorial/summary`

- Status: `skipped_mutating`
- Tested path: `/users/self/consultant/tutorial/summary`
- Reason: PATCH may mutate remote state; not executed by inventory test.
