# `/video-courses`

- URL template: `https://api.worldquantbrain.com/video-courses`
- Methods: `GET`
- Sources: `platform_frontend`
- Safe probe: `True`
- Description: Video courses. / Discovered from platform frontend bundle.

## Probe

- Probe URL: `https://api.worldquantbrain.com/video-courses`
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
      "videos": [
        "..."
      ],
      "title": "str",
      "sequence": "int",
      "description": "str",
      "lastModified": "str"
    }
  ]
}
```

## Endpoint Tests

### `GET /video-courses`

- Status: `tested`
- Tested path: `/video-courses`
- HTTP: `200 OK`
- Elapsed: `421 ms`
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
      "description": "str",
      "id": "str",
      "lastModified": "str",
      "sequence": "int",
      "title": "str",
      "videos": [
        "dict"
      ]
    }
  ]
}
```
