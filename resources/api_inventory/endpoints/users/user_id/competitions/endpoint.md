# `/users/{user_id}/competitions`

- URL template: `https://api.worldquantbrain.com/users/{user_id}/competitions`
- Methods: `GET`
- Sources: `observed_platform, platform_dynamic_capture`
- Safe probe: `False`
- Description: User competitions by id.

## Probe

- Skipped

## Dynamic Capture

### `GET /users/JL40454/competitions`

- Seen count: `14`
- Status codes: `200`
- Query keys: ``
- Content types: `application/json`

#### Response Shape

```json
{
  "count": "int",
  "next": "null",
  "previous": "null",
  "results": [
    {
      "countries": "null",
      "description": "str",
      "endDate": "str",
      "excludedCountries": "null",
      "faq": "str",
      "id": "str",
      "leaderboard": {
        "alphas": "int",
        "country": "str",
        "minCoverage": "int",
        "notebookSubmission": "int",
        "presentationSubmission": "int",
        "rank": "int",
        "score": "float",
        "university": "str",
        "user": "str"
      },
      "name": "str",
      "prizeBoard": "bool",
      "progress": "null",
      "scoring": "str",
      "signUpDate": "str",
      "signUpEndDate": "str",
      "signUpStartDate": "str",
      "startDate": "str",
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

### `GET /users/{user_id}/competitions`

- Status: `tested`
- Tested path: `/users/JL40454/competitions`
- HTTP: `200 OK`
- Elapsed: `801 ms`
- Content-Type: `application/json`
- Allow: `GET, HEAD, OPTIONS`

#### Tested Response Shape

```json
{
  "count": "int",
  "next": "null",
  "previous": "null",
  "results": [
    {
      "countries": "null",
      "description": "str",
      "endDate": "str",
      "excludedCountries": "null",
      "faq": "str",
      "id": "str",
      "leaderboard": {
        "alphas": "int",
        "country": "str",
        "minCoverage": "int",
        "notebookSubmission": "int",
        "presentationSubmission": "int",
        "rank": "int",
        "score": "float",
        "university": "str",
        "user": "str"
      },
      "name": "str",
      "prizeBoard": "bool",
      "progress": "null",
      "scoring": "str",
      "signUpDate": "str",
      "signUpEndDate": "str",
      "signUpStartDate": "str",
      "startDate": "str",
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
