# `/users/{user_id}/activities`

- URL template: `https://api.worldquantbrain.com/users/{user_id}/activities`
- Methods: `GET`
- Sources: `observed_platform`
- Safe probe: `False`
- Description: User activities by id.

## Probe

- Skipped

## Endpoint Tests

### `GET /users/{user_id}/activities`

- Status: `tested`
- Tested path: `/users/JL40454/activities`
- HTTP: `200 OK`
- Elapsed: `263 ms`
- Content-Type: `application/json`
- Allow: `GET, HEAD, OPTIONS`

#### Tested Response Shape

```json
{
  "count": "int",
  "next": "null",
  "previous": "null",
  "results": [
    {
      "name": "str",
      "title": "str"
    }
  ]
}
```

## API refresh 2026-09-22

User activities by id.

- Advertised methods: GET, HEAD.
- Live OPTIONS status: 405. Mutation methods were not executed.
- Account-specific option values are omitted; use `wqb api call` with OPTIONS for current metadata.
