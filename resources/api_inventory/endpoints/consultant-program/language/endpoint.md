# `/consultant-program/{language}`

- URL template: `https://api.worldquantbrain.com/consultant-program/{language}`
- Methods: `GET`
- Sources: `platform_frontend`
- Safe probe: `False`
- Description: Consultant program by language. / Discovered from platform frontend bundle.

## Probe

- Skipped

## Endpoint Tests

### `GET /consultant-program/{language}`

- Status: `tested`
- Tested path: `/consultant-program/en`
- HTTP: `404 Not Found`
- Elapsed: `255 ms`
- Content-Type: `application/json`

#### Tested Response Shape

```json
{
  "detail": "str"
}
```

## API refresh 2026-09-22

Consultant program by language. / Discovered from platform frontend bundle.

- Advertised methods: GET.
- Live OPTIONS status: 404. Mutation methods were not executed.
- Account-specific option values are omitted; use `wqb api call` with OPTIONS for current metadata.
