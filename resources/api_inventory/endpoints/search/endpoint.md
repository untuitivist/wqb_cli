# `/search`

- URL template: `https://api.worldquantbrain.com/search`
- Methods: `GET`
- Sources: `platform_frontend`
- Safe probe: `True`
- Description: Global search. / Discovered from platform frontend bundle.
- Params: `{"query": "search text"}`

## Probe

- Probe URL: `https://api.worldquantbrain.com/search`
- Allowed methods: `GET, HEAD, OPTIONS`
- Status: `400 Bad Request`
- Usable GET: `False`

### Response Shape

```json
{
  "query": [
    "str"
  ]
}
```

## Endpoint Tests

### `GET /search`

- Status: `tested`
- Tested path: `/search`
- HTTP: `400 Bad Request`
- Elapsed: `264 ms`
- Content-Type: `application/json`
- Allow: `GET, HEAD, OPTIONS`

#### Tested Response Shape

```json
{
  "query": [
    "str"
  ]
}
```
