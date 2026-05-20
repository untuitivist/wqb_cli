# `/data-fields/summary`

- URL template: `https://api.worldquantbrain.com/data-fields/summary`
- Methods: `GET`
- Sources: `platform_frontend`
- Safe probe: `True`
- Description: Data field summary aggregate. / Discovered from platform frontend bundle.

## Probe

- Probe URL: `https://api.worldquantbrain.com/data-fields/summary`
- Allowed methods: `GET, HEAD, OPTIONS`
- Status: `429 Too Many Requests`
- Usable GET: `False`

### Response Shape

```json
{
  "message": "str"
}
```

## Endpoint Tests

### `GET /data-fields/summary`

- Status: `tested`
- Tested path: `/data-fields/summary`
- HTTP: `200 OK`
- Elapsed: `1334 ms`
- Content-Type: `application/json`
- Allow: `GET, HEAD, OPTIONS`

#### Tested Response Shape

```json
[
  {
    "id": "str"
  }
]
```
