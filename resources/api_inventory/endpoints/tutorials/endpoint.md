# `/tutorials`

- URL template: `https://api.worldquantbrain.com/tutorials`
- Methods: `GET`
- Sources: `observed_platform, platform_frontend`
- Safe probe: `True`
- Description: Tutorial list. / Discovered from platform frontend bundle.
- Params: `{"limit": "optional", "query": "limit=50"}`

## Probe

- Probe URL: `https://api.worldquantbrain.com/tutorials?limit=1`
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
      "category": "str",
      "pages": [
        "..."
      ],
      "title": "str",
      "sequence": "int",
      "lastModified": "str"
    }
  ]
}
```

## Endpoint Tests

### `GET /tutorials`

- Status: `tested`
- Tested path: `/tutorials`
- HTTP: `200 OK`
- Elapsed: `284 ms`
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
      "category": "str",
      "id": "str",
      "lastModified": "str",
      "pages": [
        "dict"
      ],
      "sequence": "int",
      "title": "str"
    }
  ]
}
```
