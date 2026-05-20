# `/tutorial-pages/{page_id}`

- URL template: `https://api.worldquantbrain.com/tutorial-pages/{page_id}`
- Methods: `GET`
- Sources: `observed_platform`
- Safe probe: `False`
- Description: Tutorial page details.

## Probe

- Skipped

## Endpoint Tests

### `GET /tutorial-pages/{page_id}`

- Status: `tested`
- Tested path: `/tutorial-pages/exclusive-events-and-support-for-consultants`
- HTTP: `404 Not Found`
- Elapsed: `338 ms`
- Content-Type: `application/json`
- Allow: `GET, HEAD, OPTIONS`

#### Tested Response Shape

```json
{
  "message": "str"
}
```
