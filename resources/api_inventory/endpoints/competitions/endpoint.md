# `/competitions`

- URL template: `https://api.worldquantbrain.com/competitions`
- Methods: `GET`
- Sources: `observed_platform, platform_dynamic_capture, platform_frontend`
- Safe probe: `True`
- Description: Competitions list. / Discovered from platform frontend bundle.
- Params: `{"limit": "optional", "offset": "optional"}`

## Probe

- Probe URL: `https://api.worldquantbrain.com/competitions?limit=1`
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
      "name": "str",
      "description": "str",
      "universities": "NoneType",
      "countries": "NoneType",
      "excludedCountries": "NoneType",
      "status": "str",
      "teamBased": "bool",
      "startDate": "NoneType",
      "endDate": "NoneType",
      "signUpStartDate": "NoneType",
      "signUpEndDate": "NoneType",
      "signUpDate": "NoneType",
      "team": "NoneType",
      "scoring": "str",
      "leaderboard": "NoneType",
      "prizeBoard": "bool",
      "universityBoard": "bool",
      "submissions": "bool",
      "faq": "str",
      "progress": "NoneType"
    }
  ]
}
```

## Dynamic Capture

### `GET /competitions`

- Seen count: `1`
- Status codes: `200`
- Query keys: `limit, offset`
- Content types: `application/json`

#### Response Shape

```json
{
  "count": "int",
  "next": "str",
  "previous": "null",
  "results": [
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
  ]
}
```

## Endpoint Tests

### `GET /competitions`

- Status: `tested`
- Tested path: `/competitions`
- HTTP: `200 OK`
- Elapsed: `278 ms`
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
  ]
}
```
