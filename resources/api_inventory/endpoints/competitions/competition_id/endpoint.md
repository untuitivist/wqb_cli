# `/competitions/{competition_id}`

- URL template: `https://api.worldquantbrain.com/competitions/{competition_id}`
- Methods: `GET`
- Sources: `observed_platform`
- Safe probe: `False`
- Description: Competition details.

## Probe

- Skipped

## Endpoint Tests

### `GET /competitions/{competition_id}`

- Status: `tested`
- Tested path: `/competitions/challenge`
- HTTP: `200 OK`
- Elapsed: `278 ms`
- Content-Type: `application/json`
- Allow: `GET, HEAD, OPTIONS`

#### Tested Response Shape

```json
{
  "countries": "null",
  "description": "str",
  "endDate": "null",
  "excludedCountries": "null",
  "faq": "str",
  "id": "str",
  "leaderboard": "null",
  "name": "str",
  "prizeBoard": "bool",
  "progress": "null",
  "scoring": "str",
  "signUpDate": "null",
  "signUpEndDate": "null",
  "signUpStartDate": "null",
  "startDate": "null",
  "status": "str",
  "submissions": "bool",
  "team": "null",
  "teamBased": "bool",
  "universities": "null",
  "universityBoard": "bool"
}
```

## API refresh 2026-09-22

Competition details.

- Advertised methods: GET.
- Live OPTIONS status: SKIPPED_NO_OBSERVED_ID. Mutation methods were not executed.
- Account-specific option values are omitted; use `wqb api call` with OPTIONS for current metadata.
