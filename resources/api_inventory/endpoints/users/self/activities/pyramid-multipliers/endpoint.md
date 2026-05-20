# `/users/self/activities/pyramid-multipliers`

- URL template: `https://api.worldquantbrain.com/users/self/activities/pyramid-multipliers`
- Methods: `GET`
- Sources: `observed_platform`
- Safe probe: `True`
- Description: Current user's pyramid multipliers.

## Probe

- Probe URL: `https://api.worldquantbrain.com/users/self/activities/pyramid-multipliers`
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
      "multiplier": "float"
    }
  ]
}
```

## Endpoint Tests

### `GET /users/self/activities/pyramid-multipliers`

- Status: `tested`
- Tested path: `/users/self/activities/pyramid-multipliers`
- HTTP: `200 OK`
- Elapsed: `274 ms`
- Content-Type: `application/json`
- Allow: `GET, HEAD, OPTIONS`

#### Tested Response Shape

```json
{
  "pyramids": [
    {
      "category": {
        "id": "str",
        "name": "str"
      },
      "delay": "int",
      "multiplier": "float",
      "region": "str"
    }
  ]
}
```
