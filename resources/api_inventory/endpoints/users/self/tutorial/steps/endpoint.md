# `/users/self/tutorial/steps`

- URL template: `https://api.worldquantbrain.com/users/self/tutorial/steps`
- Methods: `GET`
- Sources: `platform_frontend`
- Safe probe: `True`
- Description: Tutorial step state. / Discovered from platform frontend bundle.

## Probe

- Probe URL: `https://api.worldquantbrain.com/users/self/tutorial/steps`
- Allowed methods: `GET, HEAD, OPTIONS`
- Status: `200 OK`
- Usable GET: `True`

### Response Shape

```json
[
  {
    "name": "str",
    "task": "str",
    "hint": "str",
    "answer": "str",
    "slug": "str",
    "stepIndex": "int"
  }
]
```

## Endpoint Tests

### `GET /users/self/tutorial/steps`

- Status: `tested`
- Tested path: `/users/self/tutorial/steps`
- HTTP: `200 OK`
- Elapsed: `271 ms`
- Content-Type: `application/json`
- Allow: `GET, HEAD, OPTIONS`

#### Tested Response Shape

```json
[
  {
    "answer": "str",
    "hint": "str",
    "name": "str",
    "slug": "str",
    "stepIndex": "int",
    "task": "str"
  }
]
```
