# `/competitions/{competition_id}/agreement`

- URL template: `https://api.worldquantbrain.com/competitions/{competition_id}/agreement`
- Methods: `GET, POST`
- Sources: `observed_platform`
- Safe probe: `False`
- Description: Competition agreement.
- Request body: POST may accept agreement.

## Probe

- Skipped

## Endpoint Tests

### `GET /competitions/{competition_id}/agreement`

- Status: `tested`
- Tested path: `/competitions/challenge/agreement`
- HTTP: `200 OK`
- Elapsed: `269 ms`
- Content-Type: `application/json`
- Allow: `GET, HEAD, OPTIONS`

#### Tested Response Shape

```json
{
  "content": [
    {
      "id": "str",
      "type": "str",
      "value": "str"
    }
  ],
  "id": "str",
  "lastModified": "str",
  "title": "str"
}
```
### `POST /competitions/{competition_id}/agreement`

- Status: `skipped_mutating`
- Tested path: `/competitions/challenge/agreement`
- Reason: POST may mutate remote state; not executed by inventory test.
