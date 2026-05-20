# `/users/self/activities/pyramid-alphas`

- URL template: `https://api.worldquantbrain.com/users/self/activities/pyramid-alphas`
- Methods: `GET`
- Sources: `observed_platform`
- Safe probe: `True`
- Description: Current user's pyramid alpha counts.
- Params: `{"startDate": "YYYY-MM-DD", "endDate": "YYYY-MM-DD"}`

## Probe

- Probe URL: `https://api.worldquantbrain.com/users/self/activities/pyramid-alphas`
- Allowed methods: `GET, HEAD, OPTIONS`
- Status: `200 OK`
- Usable GET: `True`

### Response Shape

```json
{
  "pyramids": [
    {
      "category": {
        "id": "...",
        "name": "..."
      },
      "region": "str",
      "delay": "int",
      "alphaCount": "int"
    }
  ]
}
```

## Endpoint Tests

### `GET /users/self/activities/pyramid-alphas`

- Status: `tested`
- Tested path: `/users/self/activities/pyramid-alphas`
- HTTP: `200 OK`
- Elapsed: `270 ms`
- Content-Type: `application/json`
- Allow: `GET, HEAD, OPTIONS`

#### Tested Response Shape

```json
{
  "pyramids": [
    {
      "alphaCount": "int",
      "category": {
        "id": "str",
        "name": "str"
      },
      "delay": "int",
      "region": "str"
    }
  ]
}
```
