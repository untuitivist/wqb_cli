# `/suggest/examples`

- URL template: `https://api.worldquantbrain.com/suggest/examples`
- Methods: `GET, POST`
- Sources: `platform_frontend`
- Safe probe: `True`
- Description: Suggestion examples. / Discovered from platform frontend bundle.

## Probe

- Probe URL: `https://api.worldquantbrain.com/suggest/examples`
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
      "settings": {
        "instrumentType": "...",
        "region": "...",
        "universe": "...",
        "delay": "...",
        "decay": "...",
        "neutralization": "...",
        "truncation": "...",
        "pasteurization": "...",
        "unitHandling": "...",
        "nanHandling": "...",
        "language": "...",
        "testPeriod": "...",
        "maxTrade": "...",
        "maxPosition": "..."
      },
      "type": "str",
      "regular": "str"
    }
  ]
}
```

## Endpoint Tests

### `GET /suggest/examples`

- Status: `tested`
- Tested path: `/suggest/examples`
- HTTP: `200 OK`
- Elapsed: `259 ms`
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
      "regular": "str",
      "settings": {
        "decay": "int",
        "delay": "int",
        "instrumentType": "str",
        "language": "str",
        "maxPosition": "str",
        "maxTrade": "str",
        "nanHandling": "str",
        "neutralization": "str",
        "pasteurization": "str",
        "region": "str",
        "testPeriod": "str",
        "truncation": "float",
        "unitHandling": "str",
        "universe": "str"
      },
      "type": "str"
    }
  ]
}
```
### `POST /suggest/examples`

- Status: `skipped_mutating`
- Tested path: `/suggest/examples`
- Reason: POST may mutate remote state; not executed by inventory test.

## API refresh 2026-09-22

Suggestion examples. / Discovered from platform frontend bundle.

- Advertised methods: GET, HEAD, OPTIONS, POST.
- Live OPTIONS status: 200. Mutation methods were not executed.
- Account-specific option values are omitted; use `wqb api call` with OPTIONS for current metadata.
