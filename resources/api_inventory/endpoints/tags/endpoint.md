# `/tags`

- URL template: `https://api.worldquantbrain.com/tags`
- Methods: `GET`
- Sources: `platform_frontend`
- Safe probe: `True`
- Description: Tag list/search. / Discovered from platform frontend bundle.

## Probe

- Probe URL: `https://api.worldquantbrain.com/tags`
- Allowed methods: `GET, POST, HEAD, OPTIONS`
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
      "name": "str",
      "alphas": [
        "..."
      ]
    }
  ]
}
```

## Endpoint Tests

### `GET /tags`

- Status: `tested`
- Tested path: `/tags`
- HTTP: `200 OK`
- Elapsed: `274 ms`
- Content-Type: `application/json`
- Allow: `GET, POST, HEAD, OPTIONS`

#### Tested Response Shape

```json
{
  "count": "int",
  "next": "str",
  "previous": "null",
  "results": [
    {
      "alphas": [
        "dict"
      ],
      "id": "str",
      "name": "str",
      "type": "str"
    }
  ]
}
```
