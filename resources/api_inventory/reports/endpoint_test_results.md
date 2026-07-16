# Endpoint Test Results

- Generated at: `2026-07-16T08:57:52+00:00`
- Endpoint count: `109`
- Method cases: `134`
- Executed safe cases: `110`
- Skipped mutating cases: `24`
- Skipped missing-sample cases: `0`
- Errors: `0`

## Sample Values

- `achievement_id`: `ALPHA_PERF_EXCELLENT`
- `alpha_id`: `vR5p8vqb`
- `competition_id`: `challenge`
- `competition_level_id`: `none`
- `dataset_id`: `analyst10`
- `event_id`: `zO8y3jm`
- `field_id`: `abnormal_news_sentiment_1d`
- `language`: `en`
- `page_id`: `exclusive-events-and-support-for-consultants`
- `record_set_name`: `pnl`
- `simulation_id`: `2UnwIe7g5jEcCgDvI4GpqO`
- `tutorial_slug`: `exclusive-events-and-support-for-consultants`
- `user_id`: `JL40454`

## Results

### `GET /achievements`

- Status: `tested`
- Tested path: `/achievements`
- HTTP: `200 OK`
- Elapsed: `255 ms`
- Content-Type: `application/json`
- Allow: `GET, HEAD, OPTIONS`

```json
[
  {
    "description": "str",
    "id": "str",
    "name": "str",
    "total": "int"
  }
]
```

### `GET /competitions/{competition_id}/boards/{board_type}`

- Status: `tested`
- Tested path: `/competitions/PAC2026/boards/leader`
- HTTP: `200 OK`
- Elapsed: `416 ms`
- Content-Type: `application/json`
- Allow: `GET, HEAD, OPTIONS`

```json
{
  "count": "int",
  "next": "str",
  "previous": "null",
  "results": [
    {
      "rank": "int",
      "user": "str",
      "alphas": "int",
      "score": "float",
      "isScore": "float",
      "osScore": "float",
      "university": "str",
      "country": "str"
    }
  ]
}
```

### `GET /competitions/spc/submissions`

- Status: `tested`
- Tested path: `/competitions/spc/submissions?limit=1&offset=0`
- HTTP: `200 OK`
- Elapsed: `243 ms`
- Content-Type: `application/json`
- Allow: `GET, POST, HEAD, OPTIONS`
- Response sample omitted because it contains user-authored prompts.

### `POST /competitions/spc/submissions`

- Status: `skipped_mutating`
- Reason: creates a remote SPC submission

### `GET /competitions/spc/submissions/{submission_id}`

- Status: `tested`
- Tested path: `/competitions/spc/submissions/{redacted}?limit=1&offset=0`
- HTTP: `200 OK`
- Elapsed: `240 ms`
- Content-Type: `application/json`
- Allow: `GET, PUT, PATCH, HEAD, OPTIONS`

```json
{
  "count": "int",
  "next": "null",
  "previous": "null",
  "results": [
    {
      "date": "str",
      "weight": "float"
    }
  ]
}
```

### `PUT /competitions/spc/submissions/{submission_id}`

- Status: `skipped_mutating`
- Reason: replaces a remote SPC submission

### `PATCH /competitions/spc/submissions/{submission_id}`

- Status: `skipped_mutating`
- Reason: updates a remote SPC submission

### `GET /consultant/boards/{board_type}`

- Status: `tested`
- Tested path: `/consultant/boards/spc?limit=1&offset=0`
- HTTP: `200 OK`
- Elapsed: `693 ms`
- Content-Type: `application/json`
- Allow: `GET, HEAD, OPTIONS`

### `GET /consultant/boards/spc`

- Status: `tested`
- Tested path: `/consultant/boards/spc?limit=1&offset=0`
- HTTP: `200 OK`
- Elapsed: `693 ms`
- Content-Type: `application/json`
- Allow: `GET, HEAD, OPTIONS`

### `GET /achievements/{achievement_id}/icon`

- Status: `tested`
- Tested path: `/achievements/ALPHA_PERF_EXCELLENT/icon`
- HTTP: `200 OK`
- Elapsed: `371 ms`
- Content-Type: `image/svg+xml`
- Allow: `GET, HEAD, OPTIONS`

### `GET /agreements`

- Status: `tested`
- Tested path: `/agreements`
- HTTP: `405 Method Not Allowed`
- Elapsed: `262 ms`
- Content-Type: `application/json`
- Allow: `GET, POST, HEAD, OPTIONS`

```json
{
  "detail": "str"
}
```

### `GET /alphas`

- Status: `tested`
- Tested path: `/alphas`
- HTTP: `405 Method Not Allowed`
- Elapsed: `270 ms`
- Content-Type: `application/json`
- Allow: `POST, PUT, PATCH, OPTIONS`

```json
{
  "detail": "str"
}
```

### `GET /alphas/distribution`

- Status: `tested`
- Tested path: `/alphas/distribution`
- HTTP: `404 Not Found`
- Elapsed: `271 ms`
- Content-Type: `application/json`
- Allow: `GET, PUT, PATCH, HEAD, OPTIONS`

```json
{
  "detail": "str"
}
```

### `GET /alphas/lists`

- Status: `tested`
- Tested path: `/alphas/lists`
- HTTP: `404 Not Found`
- Elapsed: `286 ms`
- Content-Type: `application/json`
- Allow: `GET, PUT, PATCH, HEAD, OPTIONS`

```json
{
  "detail": "str"
}
```

### `GET /alphas/sample-alpha-id-walkthrough`

- Status: `tested`
- Tested path: `/alphas/sample-alpha-id-walkthrough`
- HTTP: `404 Not Found`
- Elapsed: `271 ms`
- Content-Type: `application/json`
- Allow: `GET, PUT, PATCH, HEAD, OPTIONS`

```json
{
  "detail": "str"
}
```

### `GET /alphas/super-selection`

- Status: `tested`
- Tested path: `/alphas/super-selection`
- HTTP: `404 Not Found`
- Elapsed: `290 ms`
- Content-Type: `application/json`
- Allow: `GET, PUT, PATCH, HEAD, OPTIONS`

```json
{
  "detail": "str"
}
```

### `GET /alphas/unsubmitted`

- Status: `tested`
- Tested path: `/alphas/unsubmitted`
- HTTP: `404 Not Found`
- Elapsed: `265 ms`
- Content-Type: `application/json`
- Allow: `GET, PUT, PATCH, HEAD, OPTIONS`

```json
{
  "detail": "str"
}
```

### `GET /alphas/{alpha_id}`

- Status: `tested`
- Tested path: `/alphas/vR5p8vqb`
- HTTP: `200 OK`
- Elapsed: `348 ms`
- Content-Type: `application/json`
- Allow: `GET, PUT, PATCH, HEAD, OPTIONS`

```json
{
  "author": "str",
  "category": "null",
  "classifications": [
    {
      "id": "str",
      "name": "str"
    }
  ],
  "color": "null",
  "competitions": "null",
  "dateCreated": "str",
  "dateModified": "str",
  "dateSubmitted": "null",
  "favorite": "bool",
  "grade": "null",
  "hidden": "bool",
  "id": "str",
  "is": {
    "bookSize": "int",
    "checks": [
      {
        "limit": "float",
        "name": "str",
        "result": "str",
        "value": "float"
      }
    ],
    "drawdown": "float",
    "fitness": "float",
    "investabilityConstrained": {
      "bookSize": "int",
      "drawdown": "float",
      "fitness": "float",
      "longCount": "int",
      "margin": "float",
      "pnl": "int",
      "returns": "float",
      "sharpe": "float",
      "shortCount": "int",
      "turnover": "float"
    },
    "longCount": "int",
    "margin": "float",
    "pnl": "int",
    "returns": "float",
    "riskNeutralized": {
      "bookSize": "int",
      "drawdown": "float",
      "fitness": "float",
      "longCount": "int",
      "margin": "float",
      "pnl": "int",
      "returns": "float",
      "sharpe": "float",
      "shortCount": "int",
      "turnover": "float"
    },
    "sharpe": "float",
    "shortCount": "int",
    "startDate": "str",
    "turnover": "float"
  },
  "name": "null",
  "origin": "str",
  "os": "null",
  "osmosisPoints": "null",
  "prod": "null",
  "pyramidThemes": "null",
  "pyramids": "null",
  "regular": {
    "code": "str",
    "description": "null",
    "operatorCount": "int"
  },
  "settings": {
    "decay": "int",
    "delay": "int",
    "endDate": "str",
    "instrumentType": "str",
    "language": "str",
    "maxPosition": "str",
    "maxTrade": "str",
    "nanHandling": "str",
    "neutralization": "str",
    "pasteurization": "str",
    "region": "str",
    "startDate": "str",
    "testPeriod": "str",
    "truncation": "float",
    "unitHandling": "str",
    "universe": "str",
    "visualization": "bool"
  },
  "stage": "str",
  "status": "str",
  "tags": [],
  "team": "null",
  "test": {
    "bookSize": "int",
    "drawdown": "float",
    "fitness": "float",
    "investabilityConstrained": {
      "bookSize": "int",
      "drawdown": "float",
      "fitness": "float",
      "longCount": "int",
      "margin": "float",
      "pnl": "int",
      "returns": "float",
      "sharpe": "float",
      "shortCount": "int",
      "turnover": "float"
    },
    "longCount": "int",
    "margin": "float",
    "pnl": "int",
    "returns": "float",
    "riskNeutralized": {
      "bookSize": "int",
      "drawdown": "float",
      "fitness": "float",
      "longCount": "int",
      "margin": "float",
      "pnl": "int",
      "returns": "float",
      "sharpe": "float",
      "shortCount": "int",
      "turnover": "float"
    },
    "sharpe": "float",
    "shortCount": "int",
    "startDate": "str",
    "turnover": "float"
  },
  "themes": "null",
  "train": {
    "bookSize": "int",
    "drawdown": "float",
    "fitness": "float",
    "investabilityConstrained": {
      "bookSize": "int",
      "drawdown": "float",
      "fitness": "float",
      "longCount": "int",
      "margin": "float",
      "pnl": "int",
      "returns": "float",
      "sharpe": "float",
      "shortCount": "int",
      "turnover": "float"
    },
    "longCount": "int",
    "margin": "float",
    "pnl": "int",
    "returns": "float",
    "riskNeutralized": {
      "bookSize": "int",
      "drawdown": "float",
      "fitness": "float",
      "longCount": "int",
      "margin": "float",
      "pnl": "int",
      "returns": "float",
      "sharpe": "float",
      "shortCount": "int",
      "turnover": "float"
    },
    "sharpe": "float",
    "shortCount": "int",
    "startDate": "str",
    "turnover": "float"
  },
  "type": "str"
}
```

### `PATCH /alphas/{alpha_id}`

- Status: `skipped_mutating`
- Tested path: `/alphas/vR5p8vqb`
- Reason: PATCH may mutate remote state; not executed by inventory test.

### `GET /alphas/{alpha_id}/alphas`

- Status: `tested`
- Tested path: `/alphas/vR5p8vqb/alphas`
- HTTP: `404 Not Found`
- Elapsed: `265 ms`
- Content-Type: `application/json`
- Allow: `GET, HEAD, OPTIONS`

```json
{
  "detail": "str"
}
```

### `GET /alphas/{alpha_id}/check`

- Status: `tested`
- Tested path: `/alphas/vR5p8vqb/check`
- HTTP: `200 OK`
- Elapsed: `617 ms`
- Content-Type: `application/json`
- Allow: `GET, PUT, PATCH, HEAD, OPTIONS`

```json
{
  "is": {
    "checks": [
      {
        "limit": "float",
        "name": "str",
        "result": "str",
        "value": "float"
      }
    ]
  }
}
```

### `GET /alphas/{alpha_id}/correlations`

- Status: `tested`
- Tested path: `/alphas/vR5p8vqb/correlations`
- HTTP: `404 Not Found`
- Elapsed: `255 ms`
- Content-Type: `application/json`

```json
{
  "detail": "str"
}
```

### `GET /alphas/{alpha_id}/correlations/power-pool`

- Status: `tested`
- Tested path: `/alphas/vR5p8vqb/correlations/power-pool`
- HTTP: `200 OK`
- Elapsed: `329 ms`
- Content-Type: `application/json`
- Allow: `GET, HEAD, OPTIONS`

```json
{
  "max": "float",
  "min": "float",
  "records": [
    [
      "str"
    ]
  ],
  "schema": {
    "name": "str",
    "properties": [
      {
        "name": "str",
        "title": "str",
        "type": "str"
      }
    ],
    "title": "str"
  }
}
```

### `GET /alphas/{alpha_id}/correlations/prod`

- Status: `tested`
- Tested path: `/alphas/vR5p8vqb/correlations/prod`
- HTTP: `200 OK`
- Elapsed: `271 ms`
- Content-Type: `application/json`
- Allow: `GET, HEAD, OPTIONS`

```json
{
  "max": "float",
  "min": "float",
  "records": [
    [
      "float"
    ]
  ],
  "schema": {
    "name": "str",
    "properties": [
      {
        "name": "str",
        "title": "str",
        "type": "str"
      }
    ],
    "title": "str"
  }
}
```

### `GET /alphas/{alpha_id}/correlations/self`

- Status: `tested`
- Tested path: `/alphas/vR5p8vqb/correlations/self`
- HTTP: `200 OK`
- Elapsed: `261 ms`
- Content-Type: `application/json`
- Allow: `GET, HEAD, OPTIONS`

```json
{
  "max": "float",
  "min": "float",
  "records": [
    [
      "str"
    ]
  ],
  "schema": {
    "name": "str",
    "properties": [
      {
        "name": "str",
        "title": "str",
        "type": "str"
      }
    ],
    "title": "str"
  }
}
```

### `GET /alphas/{alpha_id}/performance-comparison`

- Status: `tested`
- Tested path: `/alphas/vR5p8vqb/performance-comparison`
- HTTP: `404 Not Found`
- Elapsed: `257 ms`
- Content-Type: `application/json`

```json
{
  "detail": "str"
}
```

### `GET /alphas/{alpha_id}/recordsets`

- Status: `tested`
- Tested path: `/alphas/vR5p8vqb/recordsets`
- HTTP: `200 OK`
- Elapsed: `289 ms`
- Content-Type: `application/json`
- Allow: `GET, HEAD, OPTIONS`

```json
{
  "count": "int",
  "next": "null",
  "previous": "null",
  "results": [
    {
      "name": "str",
      "title": "str"
    }
  ]
}
```

### `GET /alphas/{alpha_id}/recordsets/pnl`

- Status: `tested`
- Tested path: `/alphas/vR5p8vqb/recordsets/pnl`
- HTTP: `200 OK`
- Elapsed: `390 ms`
- Content-Type: `application/json`
- Allow: `GET, HEAD, OPTIONS`

```json
{
  "records": [
    [
      "str"
    ]
  ],
  "schema": {
    "name": "str",
    "properties": [
      {
        "name": "str",
        "title": "str",
        "type": "str"
      }
    ],
    "title": "str"
  }
}
```

### `GET /alphas/{alpha_id}/recordsets/sharpe`

- Status: `tested`
- Tested path: `/alphas/vR5p8vqb/recordsets/sharpe`
- HTTP: `200 OK`
- Elapsed: `334 ms`
- Content-Type: `application/json`
- Allow: `GET, HEAD, OPTIONS`

```json
{
  "records": [
    [
      "str"
    ]
  ],
  "schema": {
    "name": "str",
    "properties": [
      {
        "name": "str",
        "title": "str",
        "type": "str"
      }
    ],
    "title": "str"
  }
}
```

### `GET /alphas/{alpha_id}/recordsets/yearly-stats`

- Status: `tested`
- Tested path: `/alphas/vR5p8vqb/recordsets/yearly-stats`
- HTTP: `200 OK`
- Elapsed: `327 ms`
- Content-Type: `application/json`
- Allow: `GET, HEAD, OPTIONS`

```json
{
  "records": [
    [
      "str"
    ]
  ],
  "schema": {
    "name": "str",
    "properties": [
      {
        "name": "str",
        "title": "str",
        "type": "str"
      }
    ],
    "title": "str"
  }
}
```

### `GET /alphas/{alpha_id}/recordsets/{record_set_name}`

- Status: `tested`
- Tested path: `/alphas/vR5p8vqb/recordsets/pnl`
- HTTP: `200 OK`
- Elapsed: `339 ms`
- Content-Type: `application/json`
- Allow: `GET, HEAD, OPTIONS`

```json
{
  "records": [
    [
      "str"
    ]
  ],
  "schema": {
    "name": "str",
    "properties": [
      {
        "name": "str",
        "title": "str",
        "type": "str"
      }
    ],
    "title": "str"
  }
}
```

### `POST /alphas/{alpha_id}/submit`

- Status: `skipped_mutating`
- Tested path: `/alphas/vR5p8vqb/submit`
- Reason: POST may mutate remote state; not executed by inventory test.

### `DELETE /authentication`

- Status: `skipped_mutating`
- Tested path: `/authentication`
- Reason: DELETE may mutate remote state; not executed by inventory test.

### `GET /authentication`

- Status: `tested`
- Tested path: `/authentication`
- HTTP: `200 OK`
- Elapsed: `261 ms`
- Content-Type: `application/json`
- Allow: `GET, POST, DELETE, HEAD, OPTIONS`

```json
{
  "permissions": [
    "str"
  ],
  "token": {
    "expiry": "float"
  },
  "user": {
    "id": "str"
  }
}
```

### `HEAD /authentication`

- Status: `tested`
- Tested path: `/authentication`
- HTTP: `200 OK`
- Elapsed: `268 ms`
- Content-Type: `application/json`
- Allow: `GET, POST, DELETE, HEAD, OPTIONS`

### `POST /authentication`

- Status: `skipped_mutating`
- Tested path: `/authentication`
- Reason: POST may mutate remote state; not executed by inventory test.

### `GET /authentication/brainlabs`

- Status: `tested`
- Tested path: `/authentication/brainlabs`
- HTTP: `302 Found`
- Elapsed: `256 ms`
- Allow: `GET, POST, HEAD, OPTIONS`

### `GET /authentication/persona`

- Status: `tested`
- Tested path: `/authentication/persona`
- HTTP: `400 Bad Request`
- Elapsed: `266 ms`
- Content-Type: `application/json`
- Allow: `GET, POST, HEAD, OPTIONS`

```json
[
  "str"
]
```

### `GET /authentication/support`

- Status: `tested`
- Tested path: `/authentication/support`
- HTTP: `302 Found`
- Elapsed: `1511 ms`
- Allow: `GET, HEAD, OPTIONS`

### `GET /authentication/workday`

- Status: `tested`
- Tested path: `/authentication/workday`
- HTTP: `302 Found`
- Elapsed: `260 ms`
- Allow: `GET, POST, HEAD, OPTIONS`

### `GET /captcha`

- Status: `tested`
- Tested path: `/captcha`
- HTTP: `200 OK`
- Elapsed: `270 ms`
- Content-Type: `application/json`
- Allow: `GET, POST, HEAD, OPTIONS`

```json
{
  "algorithm": "str",
  "challenge": "str",
  "maxNumber": "int",
  "salt": "str",
  "signature": "str"
}
```

### `GET /competition-levels`

- Status: `tested`
- Tested path: `/competition-levels`
- HTTP: `200 OK`
- Elapsed: `372 ms`
- Content-Type: `application/json`
- Allow: `GET, HEAD, OPTIONS`

```json
[
  {
    "id": "str",
    "name": "str"
  }
]
```

### `GET /competition-levels/{competition_level_id}/icon`

- Status: `tested`
- Tested path: `/competition-levels/none/icon`
- HTTP: `200 OK`
- Elapsed: `284 ms`
- Content-Type: `image/svg+xml`
- Allow: `GET, HEAD, OPTIONS`

### `GET /competitions`

- Status: `tested`
- Tested path: `/competitions`
- HTTP: `200 OK`
- Elapsed: `278 ms`
- Content-Type: `application/json`
- Allow: `GET, HEAD, OPTIONS`

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

### `GET /competitions/{competition_id}`

- Status: `tested`
- Tested path: `/competitions/challenge`
- HTTP: `200 OK`
- Elapsed: `278 ms`
- Content-Type: `application/json`
- Allow: `GET, HEAD, OPTIONS`

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

### `GET /competitions/{competition_id}/agreement`

- Status: `tested`
- Tested path: `/competitions/challenge/agreement`
- HTTP: `200 OK`
- Elapsed: `269 ms`
- Content-Type: `application/json`
- Allow: `GET, HEAD, OPTIONS`

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

### `GET /configuration`

- Status: `tested`
- Tested path: `/configuration`
- HTTP: `200 OK`
- Elapsed: `253 ms`
- Content-Type: `application/json`
- Allow: `GET, HEAD, OPTIONS`

```json
{
  "analytics": {
    "trackingId": "null"
  },
  "recaptcha": {
    "siteKey": "str"
  },
  "recaptchaV3": {
    "siteKey": "str"
  }
}
```

### `GET /consultant`

- Status: `tested`
- Tested path: `/consultant`
- HTTP: `404 Not Found`
- Elapsed: `267 ms`
- Content-Type: `application/json`

```json
{
  "detail": "str"
}
```

### `GET /consultant-datasets`

- Status: `tested`
- Tested path: `/consultant-datasets`
- HTTP: `404 Not Found`
- Elapsed: `255 ms`
- Content-Type: `application/json`

```json
{
  "detail": "str"
}
```

### `GET /consultant-information/consultant-dos-and-donts`

- Status: `tested`
- Tested path: `/consultant-information/consultant-dos-and-donts`
- HTTP: `404 Not Found`
- Elapsed: `258 ms`
- Content-Type: `application/json`

```json
{
  "detail": "str"
}
```

### `GET /consultant-information/consultant-faqs`

- Status: `tested`
- Tested path: `/consultant-information/consultant-faqs`
- HTTP: `404 Not Found`
- Elapsed: `261 ms`
- Content-Type: `application/json`

```json
{
  "detail": "str"
}
```

### `GET /consultant-information/osmosis-allocation-guide-consultants`

- Status: `tested`
- Tested path: `/consultant-information/osmosis-allocation-guide-consultants`
- HTTP: `404 Not Found`
- Elapsed: `259 ms`
- Content-Type: `application/json`

```json
{
  "detail": "str"
}
```

### `GET /consultant-information/visualization-tool`

- Status: `tested`
- Tested path: `/consultant-information/visualization-tool`
- HTTP: `404 Not Found`
- Elapsed: `255 ms`
- Content-Type: `application/json`

```json
{
  "detail": "str"
}
```

### `GET /consultant-program`

- Status: `tested`
- Tested path: `/consultant-program`
- HTTP: `404 Not Found`
- Elapsed: `258 ms`
- Content-Type: `application/json`

```json
{
  "detail": "str"
}
```

### `GET /consultant-program/{language}`

- Status: `tested`
- Tested path: `/consultant-program/en`
- HTTP: `404 Not Found`
- Elapsed: `255 ms`
- Content-Type: `application/json`

```json
{
  "detail": "str"
}
```

### `GET /consultant/boards`

- Status: `tested`
- Tested path: `/consultant/boards`
- HTTP: `404 Not Found`
- Elapsed: `255 ms`
- Content-Type: `application/json`

```json
{
  "detail": "str"
}
```

### `GET /consultant/boards/leader`

- Status: `tested`
- Tested path: `/consultant/boards/leader`
- HTTP: `200 OK`
- Elapsed: `378 ms`
- Content-Type: `application/json`
- Allow: `GET, HEAD, OPTIONS`

```json
{
  "count": "int",
  "next": "str",
  "previous": "null",
  "results": [
    {
      "country": "str",
      "dailyOsmosisRank": "float",
      "dataFieldsUsed": "int",
      "meanProdCorrelation": "float",
      "meanSelfCorrelation": "float",
      "submissionsCount": "int",
      "superAlphaMeanProdCorrelation": "float",
      "superAlphaMeanSelfCorrelation": "float",
      "superAlphaSubmissionsCount": "int",
      "university": "str",
      "user": "str",
      "valueFactor": "float",
      "weightFactor": "float"
    }
  ]
}
```

### `GET /consultant/summary`

- Status: `tested`
- Tested path: `/consultant/summary`
- HTTP: `404 Not Found`
- Elapsed: `255 ms`
- Content-Type: `application/json`

```json
{
  "detail": "str"
}
```

### `GET /data-categories`

- Status: `tested`
- Tested path: `/data-categories`
- HTTP: `200 OK`
- Elapsed: `1270 ms`
- Content-Type: `application/json`
- Allow: `GET, HEAD, OPTIONS`

```json
[
  {
    "alphaCount": "int",
    "children": [
      {
        "alphaCount": "int",
        "datasetCount": "int",
        "fieldCount": "int",
        "id": "str",
        "name": "str",
        "region": "list",
        "userCount": "int",
        "valueScore": "float"
      }
    ],
    "datasetCount": "int",
    "fieldCount": "int",
    "id": "str",
    "name": "str",
    "region": [
      "str"
    ],
    "userCount": "int",
    "valueScore": "float"
  }
]
```

### `GET /data-fields`

- Status: `tested`
- Tested path: `/data-fields`
- HTTP: `200 OK`
- Elapsed: `255 ms`
- Content-Type: `application/json`
- Allow: `GET, HEAD, OPTIONS`

```json
{
  "count": "int",
  "results": [
    {
      "alphaCount": "int",
      "category": {
        "id": "str",
        "name": "str"
      },
      "coverage": "float",
      "dataset": {
        "id": "str",
        "name": "str"
      },
      "dateCoverage": "float",
      "delay": "int",
      "description": "str",
      "id": "str",
      "pyramidMultiplier": "float",
      "region": "str",
      "subcategory": {
        "id": "str",
        "name": "str"
      },
      "themes": [],
      "type": "str",
      "universe": "str",
      "userCount": "int"
    }
  ]
}
```

### `GET /data-fields/summary`

- Status: `tested`
- Tested path: `/data-fields/summary`
- HTTP: `200 OK`
- Elapsed: `1334 ms`
- Content-Type: `application/json`
- Allow: `GET, HEAD, OPTIONS`

```json
[
  {
    "id": "str"
  }
]
```

### `GET /data-fields/{field_id}`

- Status: `tested`
- Tested path: `/data-fields/abnormal_news_sentiment_1d`
- HTTP: `200 OK`
- Elapsed: `561 ms`
- Content-Type: `application/json`
- Allow: `GET, HEAD, OPTIONS`

```json
{
  "category": {
    "id": "str",
    "name": "str"
  },
  "data": [
    {
      "alphaCount": "int",
      "coverage": "float",
      "dateCoverage": "float",
      "delay": "int",
      "pyramidMultiplier": "float",
      "region": "str",
      "themes": [],
      "universe": "str",
      "userCount": "int"
    }
  ],
  "dataset": {
    "id": "str",
    "name": "str"
  },
  "description": "str",
  "id": "str",
  "subcategory": {
    "id": "str",
    "name": "str"
  },
  "type": "str",
  "visualizable": "bool"
}
```

### `GET /data-sets`

- Status: `tested`
- Tested path: `/data-sets`
- HTTP: `200 OK`
- Elapsed: `1032 ms`
- Content-Type: `application/json`
- Allow: `GET, HEAD, OPTIONS`

```json
{
  "count": "int",
  "results": [
    {
      "alphaCount": "int",
      "category": {
        "id": "str",
        "name": "str"
      },
      "coverage": "float",
      "dateCoverage": "float",
      "delay": "int",
      "description": "str",
      "fieldCount": "int",
      "id": "str",
      "name": "str",
      "pyramidMultiplier": "float",
      "region": "str",
      "researchPapers": [
        "dict"
      ],
      "subcategory": {
        "id": "str",
        "name": "str"
      },
      "themes": [],
      "universe": "str",
      "userCount": "int",
      "valueScore": "float"
    }
  ]
}
```

### `GET /data-sets/search`

- Status: `tested`
- Tested path: `/data-sets/search`
- HTTP: `400 Bad Request`
- Elapsed: `259 ms`
- Content-Type: `application/json`
- Allow: `GET, HEAD, OPTIONS`

```json
{
  "detail": "str"
}
```

### `POST /data-sets/search`

- Status: `skipped_mutating`
- Tested path: `/data-sets/search`
- Reason: POST may mutate remote state; not executed by inventory test.

### `GET /data-sets/{dataset_id}`

- Status: `tested`
- Tested path: `/data-sets/analyst10`
- HTTP: `200 OK`
- Elapsed: `5075 ms`
- Content-Type: `application/json`
- Allow: `GET, HEAD, OPTIONS`

```json
{
  "category": {
    "id": "str",
    "name": "str"
  },
  "data": [
    {
      "alphaCount": "int",
      "coverage": "float",
      "dateCoverage": "float",
      "delay": "int",
      "fieldCount": "int",
      "pyramidMultiplier": "float",
      "region": "str",
      "themes": [],
      "universe": "str",
      "userCount": "int",
      "valueScore": "float"
    }
  ],
  "description": "str",
  "id": "str",
  "name": "str",
  "researchPapers": [
    {
      "title": "str",
      "type": "str",
      "url": "str"
    }
  ],
  "subcategory": {
    "id": "str",
    "name": "str"
  }
}
```

### `POST /errors/api/2/envelope`

- Status: `skipped_mutating`
- Tested path: `/errors/api/2/envelope`
- Reason: POST may mutate remote state; not executed by inventory test.

### `GET /events`

- Status: `tested`
- Tested path: `/events`
- HTTP: `200 OK`
- Elapsed: `267 ms`
- Content-Type: `application/json`
- Allow: `GET, HEAD, OPTIONS`

```json
{
  "count": "int",
  "next": "str",
  "previous": "null",
  "results": [
    {
      "category": "null",
      "city": "null",
      "country": "str",
      "description": "str",
      "end": "str",
      "id": "str",
      "language": "str",
      "register": "str",
      "start": "str",
      "timezone": "str",
      "title": "str",
      "type": "str",
      "venue": "null"
    }
  ]
}
```

### `OPTIONS /events`

- Status: `tested`
- Tested path: `/events`
- HTTP: `200 OK`
- Elapsed: `264 ms`
- Content-Type: `application/json`
- Allow: `GET, HEAD, OPTIONS`

```json
{
  "actions": {
    "GET": {
      "category": {
        "choices": "list",
        "label": "str",
        "readOnly": "bool",
        "required": "bool",
        "type": "str"
      },
      "city": {
        "choices": "list",
        "label": "str",
        "readOnly": "bool",
        "required": "bool",
        "type": "str"
      },
      "country": {
        "choices": "list",
        "label": "str",
        "readOnly": "bool",
        "required": "bool",
        "type": "str"
      },
      "description": {
        "label": "str",
        "maxLength": "int",
        "readOnly": "bool",
        "required": "bool",
        "type": "str"
      },
      "end": {
        "label": "str",
        "readOnly": "bool",
        "required": "bool",
        "type": "str"
      },
      "id": {
        "label": "str",
        "readOnly": "bool",
        "required": "bool",
        "type": "str"
      },
      "language": {
        "choices": "list",
        "label": "str",
        "readOnly": "bool",
        "required": "bool",
        "type": "str"
      },
      "register": {
        "label": "str",
        "readOnly": "bool",
        "required": "bool",
        "type": "str"
      },
      "start": {
        "label": "str",
        "readOnly": "bool",
        "required": "bool",
        "type": "str"
      },
      "timezone": {
        "label": "str",
        "readOnly": "bool",
        "required": "bool",
        "type": "str"
      },
      "title": {
        "label": "str",
        "maxLength": "int",
        "readOnly": "bool",
        "required": "bool",
        "type": "str"
      },
      "type": {
        "label": "str",
        "readOnly": "bool",
        "required": "bool",
        "type": "str"
      },
      "venue": {
        "label": "str",
        "maxLength": "int",
        "readOnly": "bool",
        "required": "bool",
        "type": "str"
      }
    }
  }
}
```

### `GET /events/{event_id}`

- Status: `tested`
- Tested path: `/events/zO8y3jm`
- HTTP: `200 OK`
- Elapsed: `313 ms`
- Content-Type: `application/json`
- Allow: `GET, HEAD, OPTIONS`

```json
{
  "category": "null",
  "city": "null",
  "country": "str",
  "description": "str",
  "end": "str",
  "id": "str",
  "language": "str",
  "register": "str",
  "start": "str",
  "timezone": "str",
  "title": "str",
  "type": "str",
  "venue": "null"
}
```

### `GET /messages`

- Status: `tested`
- Tested path: `/messages`
- HTTP: `404 Not Found`
- Elapsed: `260 ms`
- Content-Type: `application/json`

```json
{
  "detail": "str"
}
```

### `GET /operators`

- Status: `tested`
- Tested path: `/operators`
- HTTP: `200 OK`
- Elapsed: `298 ms`
- Content-Type: `application/json`
- Allow: `GET, HEAD, OPTIONS`

```json
[
  {
    "category": "str",
    "definition": "str",
    "description": "str",
    "documentation": "str",
    "level": "str",
    "name": "str",
    "scope": [
      "str"
    ]
  }
]
```

### `GET /search`

- Status: `tested`
- Tested path: `/search`
- HTTP: `400 Bad Request`
- Elapsed: `264 ms`
- Content-Type: `application/json`
- Allow: `GET, HEAD, OPTIONS`

```json
{
  "query": [
    "str"
  ]
}
```

### `GET /simulations`

- Status: `tested`
- Tested path: `/simulations`
- HTTP: `405 Method Not Allowed`
- Elapsed: `257 ms`
- Content-Type: `application/json`
- Allow: `POST, OPTIONS`

```json
{
  "detail": "str"
}
```

### `OPTIONS /simulations`

- Status: `tested`
- Tested path: `/simulations`
- HTTP: `200 OK`
- Elapsed: `270 ms`
- Content-Type: `application/json`
- Allow: `POST, OPTIONS`

```json
{
  "actions": {
    "POST": {
      "alpha": {
        "label": "str",
        "readOnly": "bool",
        "required": "bool",
        "type": "str"
      },
      "children": {
        "child": "dict",
        "label": "str",
        "readOnly": "bool",
        "required": "bool",
        "type": "str"
      },
      "combo": {
        "label": "str",
        "readOnly": "bool",
        "required": "bool",
        "type": "str"
      },
      "id": {
        "label": "str",
        "readOnly": "bool",
        "required": "bool",
        "type": "str"
      },
      "is": {
        "child": "dict",
        "label": "str",
        "readOnly": "bool",
        "required": "bool",
        "type": "str"
      },
      "links": {
        "child": "dict",
        "label": "str",
        "readOnly": "bool",
        "required": "bool",
        "type": "str"
      },
      "location": {
        "child": "dict",
        "label": "str",
        "readOnly": "bool",
        "required": "bool",
        "type": "str"
      },
      "message": {
        "label": "str",
        "readOnly": "bool",
        "required": "bool",
        "type": "str"
      },
      "origin": {
        "label": "str",
        "readOnly": "bool",
        "required": "bool",
        "type": "str"
      },
      "parent": {
        "label": "str",
        "readOnly": "bool",
        "required": "bool",
        "type": "str"
      },
      "progress": {
        "label": "str",
        "readOnly": "bool",
        "required": "bool",
        "type": "str"
      },
      "regular": {
        "label": "str",
        "maxLength": "int",
        "readOnly": "bool",
        "required": "bool",
        "type": "str"
      },
      "selection": {
        "label": "str",
        "readOnly": "bool",
        "required": "bool",
        "type": "str"
      },
      "settings": {
        "children": "dict",
        "label": "str",
        "readOnly": "bool",
        "required": "bool",
        "type": "str"
      },
      "status": {
        "label": "str",
        "readOnly": "bool",
        "required": "bool",
        "type": "str"
      },
      "type": {
        "choices": "list",
        "label": "str",
        "readOnly": "bool",
        "required": "bool",
        "type": "str"
      },
      "visualizations": {
        "child": "dict",
        "label": "str",
        "readOnly": "bool",
        "required": "bool",
        "type": "str"
      }
    }
  }
}
```

### `POST /simulations`

- Status: `skipped_mutating`
- Tested path: `/simulations`
- Reason: POST may mutate remote state; not executed by inventory test.

### `GET /simulations/super-selection`

- Status: `tested`
- Tested path: `/simulations/super-selection`
- HTTP: `200 OK`
- Elapsed: `1657 ms`
- Content-Type: `application/json`
- Allow: `GET, HEAD, OPTIONS`

```json
{
  "count": "int",
  "next": "str",
  "previous": "null",
  "results": [
    {
      "author": "null",
      "category": "null",
      "classifications": [
        "dict"
      ],
      "color": "null",
      "competitions": [],
      "dateCreated": "str",
      "dateModified": "str",
      "dateSubmitted": "str",
      "favorite": "null",
      "grade": "null",
      "hidden": "null",
      "id": "str",
      "is": {
        "bookSize": "int",
        "checks": "list",
        "drawdown": "float",
        "fitness": "float",
        "investabilityConstrained": "dict",
        "longCount": "int",
        "margin": "float",
        "pnl": "int",
        "prodCorrelation": "float",
        "returns": "float",
        "riskNeutralized": "dict",
        "selfCorrelation": "float",
        "sharpe": "float",
        "shortCount": "int",
        "startDate": "str",
        "turnover": "float"
      },
      "name": "null",
      "origin": "str",
      "os": {
        "checks": "list",
        "osISSharpeRatio": "NoneType",
        "preCloseSharpeRatio": "NoneType",
        "startDate": "str"
      },
      "osmosisPoints": "null",
      "prod": "null",
      "pyramidThemes": "null",
      "pyramids": "null",
      "regular": {
        "code": "NoneType",
        "description": "NoneType",
        "operatorCount": "int"
      },
      "settings": {
        "decay": "int",
        "delay": "int",
        "endDate": "str",
        "instrumentType": "str",
        "language": "str",
        "maxPosition": "str",
        "maxTrade": "str",
        "nanHandling": "str",
        "neutralization": "str",
        "pasteurization": "str",
        "region": "str",
        "startDate": "str",
        "truncation": "float",
        "unitHandling": "str",
        "universe": "str",
        "visualization": "bool"
      },
      "stage": "str",
      "status": "str",
      "tags": [],
      "team": "null",
      "test": "null",
      "themes": [],
      "train": "null",
      "type": "str"
    }
  ]
}
```

### `POST /simulations/super-selection`

- Status: `skipped_mutating`
- Tested path: `/simulations/super-selection`
- Reason: POST may mutate remote state; not executed by inventory test.

### `GET /simulations/{simulation_id}`

- Status: `tested`
- Tested path: `/simulations/2UnwIe7g5jEcCgDvI4GpqO`
- HTTP: `200 OK`
- Elapsed: `275 ms`
- Content-Type: `application/json`
- Allow: `GET, DELETE, HEAD, OPTIONS`

```json
{
  "alpha": "str",
  "id": "str",
  "links": {
    "linkToCommonErrorMessages": "str"
  },
  "location": {
    "property": "str",
    "type": "str"
  },
  "message": "str",
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
    "truncation": "float",
    "unitHandling": "str",
    "universe": "str",
    "visualization": "bool"
  },
  "status": "str",
  "type": "str"
}
```

### `GET /suggest/examples`

- Status: `tested`
- Tested path: `/suggest/examples`
- HTTP: `200 OK`
- Elapsed: `259 ms`
- Content-Type: `application/json`
- Allow: `GET, HEAD, OPTIONS`

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

### `GET /suggest/expression`

- Status: `tested`
- Tested path: `/suggest/expression`
- HTTP: `404 Not Found`
- Elapsed: `257 ms`
- Content-Type: `application/json`

```json
{
  "detail": "str"
}
```

### `POST /suggest/expression`

- Status: `skipped_mutating`
- Tested path: `/suggest/expression`
- Reason: POST may mutate remote state; not executed by inventory test.

### `GET /suggest/fastexpr`

- Status: `tested`
- Tested path: `/suggest/fastexpr`
- HTTP: `404 Not Found`
- Elapsed: `282 ms`
- Content-Type: `application/json`

```json
{
  "detail": "str"
}
```

### `POST /suggest/fastexpr`

- Status: `skipped_mutating`
- Tested path: `/suggest/fastexpr`
- Reason: POST may mutate remote state; not executed by inventory test.

### `GET /suggest/fields`

- Status: `tested`
- Tested path: `/suggest/fields`
- HTTP: `200 OK`
- Elapsed: `314 ms`
- Content-Type: `application/json`
- Allow: `GET, HEAD, OPTIONS`

```json
{
  "combo": [
    "str"
  ],
  "selection": [
    "str"
  ]
}
```

### `POST /suggest/fields`

- Status: `skipped_mutating`
- Tested path: `/suggest/fields`
- Reason: POST may mutate remote state; not executed by inventory test.

### `GET /tags`

- Status: `tested`
- Tested path: `/tags`
- HTTP: `200 OK`
- Elapsed: `274 ms`
- Content-Type: `application/json`
- Allow: `GET, POST, HEAD, OPTIONS`

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

### `GET /teams`

- Status: `tested`
- Tested path: `/teams`
- HTTP: `405 Method Not Allowed`
- Elapsed: `260 ms`
- Content-Type: `application/json`
- Allow: `POST, OPTIONS`

```json
{
  "detail": "str"
}
```

### `GET /tutorial-pages`

- Status: `tested`
- Tested path: `/tutorial-pages`
- HTTP: `404 Not Found`
- Elapsed: `255 ms`
- Content-Type: `application/json`
- Allow: `GET, HEAD, OPTIONS`

```json
{
  "message": "str"
}
```

### `GET /tutorial-pages/{page_id}`

- Status: `tested`
- Tested path: `/tutorial-pages/exclusive-events-and-support-for-consultants`
- HTTP: `404 Not Found`
- Elapsed: `338 ms`
- Content-Type: `application/json`
- Allow: `GET, HEAD, OPTIONS`

```json
{
  "message": "str"
}
```

### `GET /tutorial/{tutorial_slug}`

- Status: `tested`
- Tested path: `/tutorial/exclusive-events-and-support-for-consultants`
- HTTP: `200 OK`
- Elapsed: `289 ms`
- Content-Type: `application/json`
- Allow: `GET, HEAD, OPTIONS`

```json
{
  "category": "str",
  "content": [
    {
      "id": "str",
      "type": "str",
      "value": {
        "content": "str",
        "level": "str"
      }
    }
  ],
  "id": "str",
  "lastModified": "str",
  "sequence": "int",
  "title": "str"
}
```

### `GET /tutorials`

- Status: `tested`
- Tested path: `/tutorials`
- HTTP: `200 OK`
- Elapsed: `284 ms`
- Content-Type: `application/json`
- Allow: `GET, HEAD, OPTIONS`

```json
{
  "count": "int",
  "next": "str",
  "previous": "null",
  "results": [
    {
      "category": "str",
      "id": "str",
      "lastModified": "str",
      "pages": [
        "dict"
      ],
      "sequence": "int",
      "title": "str"
    }
  ]
}
```

### `GET /user/email/change`

- Status: `tested`
- Tested path: `/user/email/change`
- HTTP: `405 Method Not Allowed`
- Elapsed: `257 ms`
- Content-Type: `application/json`
- Allow: `POST, OPTIONS`

```json
{
  "detail": "str"
}
```

### `POST /user/email/change`

- Status: `skipped_mutating`
- Tested path: `/user/email/change`
- Reason: POST may mutate remote state; not executed by inventory test.

### `GET /user/email/reverify`

- Status: `tested`
- Tested path: `/user/email/reverify`
- HTTP: `405 Method Not Allowed`
- Elapsed: `261 ms`
- Content-Type: `application/json`
- Allow: `POST, OPTIONS`

```json
{
  "detail": "str"
}
```

### `POST /user/email/reverify`

- Status: `skipped_mutating`
- Tested path: `/user/email/reverify`
- Reason: POST may mutate remote state; not executed by inventory test.

### `GET /user/email/verify`

- Status: `tested`
- Tested path: `/user/email/verify`
- HTTP: `405 Method Not Allowed`
- Elapsed: `259 ms`
- Content-Type: `application/json`
- Allow: `POST, OPTIONS`

```json
{
  "detail": "str"
}
```

### `POST /user/email/verify`

- Status: `skipped_mutating`
- Tested path: `/user/email/verify`
- Reason: POST may mutate remote state; not executed by inventory test.

### `GET /user/password/change`

- Status: `tested`
- Tested path: `/user/password/change`
- HTTP: `405 Method Not Allowed`
- Elapsed: `265 ms`
- Content-Type: `application/json`
- Allow: `POST, OPTIONS`

```json
{
  "detail": "str"
}
```

### `POST /user/password/change`

- Status: `skipped_mutating`
- Tested path: `/user/password/change`
- Reason: POST may mutate remote state; not executed by inventory test.

### `GET /user/password/forgot`

- Status: `tested`
- Tested path: `/user/password/forgot`
- HTTP: `405 Method Not Allowed`
- Elapsed: `264 ms`
- Content-Type: `application/json`
- Allow: `POST, OPTIONS`

```json
{
  "detail": "str"
}
```

### `POST /user/password/forgot`

- Status: `skipped_mutating`
- Tested path: `/user/password/forgot`
- Reason: POST may mutate remote state; not executed by inventory test.

### `GET /user/password/reset`

- Status: `tested`
- Tested path: `/user/password/reset`
- HTTP: `405 Method Not Allowed`
- Elapsed: `258 ms`
- Content-Type: `application/json`
- Allow: `POST, OPTIONS`

```json
{
  "detail": "str"
}
```

### `POST /user/password/reset`

- Status: `skipped_mutating`
- Tested path: `/user/password/reset`
- Reason: POST may mutate remote state; not executed by inventory test.

### `GET /user/token`

- Status: `tested`
- Tested path: `/user/token`
- HTTP: `405 Method Not Allowed`
- Elapsed: `262 ms`
- Content-Type: `application/json`
- Allow: `POST, OPTIONS`

```json
{
  "detail": "str"
}
```

### `POST /user/token`

- Status: `skipped_mutating`
- Tested path: `/user/token`
- Reason: POST may mutate remote state; not executed by inventory test.

### `GET /users`

- Status: `tested`
- Tested path: `/users`
- HTTP: `405 Method Not Allowed`
- Elapsed: `268 ms`
- Content-Type: `application/json`
- Allow: `POST, OPTIONS`

```json
{
  "detail": "str"
}
```

### `GET /users/self`

- Status: `tested`
- Tested path: `/users/self`
- HTTP: `200 OK`
- Elapsed: `297 ms`
- Content-Type: `application/json`
- Allow: `GET, PUT, PATCH, DELETE, HEAD, OPTIONS`

```json
{
  "address": {
    "city": "str",
    "country": "str",
    "postalCode": "null",
    "state": "null",
    "street": "null"
  },
  "approved": "bool",
  "auxiliary": {
    "campaign": {
      "campaign": "str",
      "content": "str",
      "medium": "str",
      "source": "str",
      "term": "null"
    }
  },
  "dateApproved": "str",
  "dateCreated": "str",
  "dateVerified": "str",
  "education": {
    "degree": "str",
    "gpa": "float",
    "graduationYear": "int",
    "major": "str",
    "maxGPA": "float",
    "stem": "bool",
    "university": "str"
  },
  "email": "str",
  "employment": "null",
  "firstName": "str",
  "fullName": "str",
  "gender": "str",
  "geniusLevel": "str",
  "id": "str",
  "image": {
    "url": "str"
  },
  "lastName": "str",
  "onboarding": {
    "status": "str"
  },
  "recruitment": {
    "codingProficiency": "str",
    "englishProficiency": "str",
    "roleInterest": [
      "str"
    ]
  },
  "resume": {
    "dateCreated": "str"
  },
  "settings": {
    "allowTracking": "bool",
    "client": {},
    "communication": {
      "allowSMS": "bool"
    },
    "privacy": {
      "image": {
        "moderation": "str",
        "visibility": "str"
      },
      "name": {
        "moderation": "str",
        "visibility": "str"
      }
    }
  },
  "telephone": "str",
  "verified": "bool"
}
```

### `GET /users/self/achievements`

- Status: `tested`
- Tested path: `/users/self/achievements`
- HTTP: `200 OK`
- Elapsed: `621 ms`
- Content-Type: `application/json`
- Allow: `GET, HEAD, OPTIONS`

```json
[
  {
    "achieved": "str",
    "description": "str",
    "id": "str",
    "name": "str",
    "ratio": "float",
    "total": "int",
    "value": "int"
  }
]
```

### `GET /users/self/activities/pyramid-alphas`

- Status: `tested`
- Tested path: `/users/self/activities/pyramid-alphas`
- HTTP: `200 OK`
- Elapsed: `270 ms`
- Content-Type: `application/json`
- Allow: `GET, HEAD, OPTIONS`

```json
{
  "pyramids": [
    {
      "alphaCount": "int",
      "category": {
        "id": "str",
        "name": "str"
      },
      "delay": "int",
      "region": "str"
    }
  ]
}
```

### `GET /users/self/activities/pyramid-multipliers`

- Status: `tested`
- Tested path: `/users/self/activities/pyramid-multipliers`
- HTTP: `200 OK`
- Elapsed: `274 ms`
- Content-Type: `application/json`
- Allow: `GET, HEAD, OPTIONS`

```json
{
  "pyramids": [
    {
      "category": {
        "id": "str",
        "name": "str"
      },
      "delay": "int",
      "multiplier": "float",
      "region": "str"
    }
  ]
}
```

### `GET /users/self/activities/simulations`

- Status: `tested`
- Tested path: `/users/self/activities/simulations`
- HTTP: `200 OK`
- Elapsed: `268 ms`
- Content-Type: `application/json`
- Allow: `GET, HEAD, OPTIONS`

```json
{
  "current": {
    "end": "str",
    "start": "str",
    "value": "int"
  },
  "previous": {
    "end": "str",
    "start": "str",
    "value": "int"
  },
  "records": {
    "records": [
      [
        "str"
      ]
    ],
    "schema": {
      "name": "str",
      "properties": [
        "dict"
      ],
      "title": "str"
    }
  },
  "total": {
    "end": "str",
    "start": "str",
    "value": "int"
  },
  "type": "str",
  "yesterday": {
    "end": "str",
    "start": "str",
    "value": "int"
  },
  "ytd": {
    "end": "str",
    "start": "str",
    "value": "int"
  }
}
```

### `GET /users/self/agreements`

- Status: `tested`
- Tested path: `/users/self/agreements`
- HTTP: `200 OK`
- Elapsed: `288 ms`
- Content-Type: `application/json`
- Allow: `GET, HEAD, OPTIONS`

```json
[
  {
    "agreement": {
      "id": "str",
      "name": "str"
    },
    "status": "str",
    "statusDate": "str"
  }
]
```

### `GET /users/self/alphas`

- Status: `tested`
- Tested path: `/users/self/alphas`
- HTTP: `200 OK`
- Elapsed: `626 ms`
- Content-Type: `application/json`
- Allow: `GET, HEAD, OPTIONS`

```json
{
  "count": "int",
  "next": "str",
  "previous": "null",
  "results": [
    {
      "author": "str",
      "category": "null",
      "classifications": [
        "dict"
      ],
      "color": "null",
      "competitions": "null",
      "dateCreated": "str",
      "dateModified": "str",
      "dateSubmitted": "null",
      "favorite": "bool",
      "grade": "null",
      "hidden": "bool",
      "id": "str",
      "is": {
        "bookSize": "int",
        "checks": "list",
        "drawdown": "float",
        "fitness": "float",
        "investabilityConstrained": "dict",
        "longCount": "int",
        "margin": "float",
        "pnl": "int",
        "returns": "float",
        "riskNeutralized": "dict",
        "sharpe": "float",
        "shortCount": "int",
        "startDate": "str",
        "turnover": "float"
      },
      "name": "null",
      "origin": "str",
      "os": "null",
      "osmosisPoints": "null",
      "prod": "null",
      "pyramidThemes": "null",
      "pyramids": "null",
      "regular": {
        "code": "str",
        "description": "NoneType",
        "operatorCount": "int"
      },
      "settings": {
        "decay": "int",
        "delay": "int",
        "endDate": "str",
        "instrumentType": "str",
        "language": "str",
        "maxPosition": "str",
        "maxTrade": "str",
        "nanHandling": "str",
        "neutralization": "str",
        "pasteurization": "str",
        "region": "str",
        "startDate": "str",
        "truncation": "float",
        "unitHandling": "str",
        "universe": "str",
        "visualization": "bool"
      },
      "stage": "str",
      "status": "str",
      "tags": [],
      "team": "null",
      "test": "null",
      "themes": "null",
      "train": "null",
      "type": "str"
    }
  ]
}
```

### `GET /users/self/alphas/summary`

- Status: `tested`
- Tested path: `/users/self/alphas/summary`
- HTTP: `200 OK`
- Elapsed: `514 ms`
- Content-Type: `application/json`
- Allow: `GET, HEAD, OPTIONS`

```json
{
  "is": "int",
  "os": "int",
  "prod": "int"
}
```

### `GET /users/self/consultant/summary`

- Status: `tested`
- Tested path: `/users/self/consultant/summary`
- HTTP: `200 OK`
- Elapsed: `2442 ms`
- Content-Type: `application/json`
- Allow: `GET, HEAD, OPTIONS`

```json
{
  "leaderboard": {
    "alphaCount": "int",
    "bestLevel": "str",
    "combinedAlphaPerformance": "float",
    "combinedOsmosisPerformance": "float",
    "combinedPowerPoolAlphaPerformance": "float",
    "combinedSelectedAlphaPerformance": "float",
    "communityActivity": "float",
    "country": "str",
    "extras": [],
    "fieldAvg": "float",
    "fieldCount": "int",
    "geniusLevel": "str",
    "maxSimulationStreak": "int",
    "operatorAvg": "float",
    "operatorCount": "int",
    "pyramidCount": "int",
    "rank": "int",
    "user": "str"
  },
  "osmosis": [
    {
      "alphas": "int",
      "delay": "int",
      "pointsAllocated": "int",
      "region": "str"
    }
  ],
  "performance": {
    "bestLevel": "str",
    "current": {
      "alphaCount": "int",
      "combinedAlphaPerformance": "float",
      "combinedOsmosisPerformance": "float",
      "combinedPowerPoolAlphaPerformance": "float",
      "combinedSelectedAlphaPerformance": "float",
      "communityActivity": "float",
      "extras": [],
      "fieldAvg": "float",
      "fieldCount": "int",
      "geniusLevel": "str",
      "level": "null",
      "maxSimulationStreak": "int",
      "operatorAvg": "float",
      "operatorCount": "int",
      "pyramidCount": "int",
      "quarter": {
        "endDate": "str",
        "name": "str",
        "startDate": "str"
      }
    },
    "currentLevel": "str",
    "currentQuarter": {
      "endDate": "str",
      "name": "str",
      "startDate": "str"
    },
    "history": [
      {
        "alphaCount": "int",
        "combinedAlphaPerformance": "float",
        "combinedSelectedAlphaPerformance": "float",
        "communityActivity": "float",
        "extras": "list",
        "fieldAvg": "float",
        "fieldCount": "int",
        "geniusLevel": "str",
        "level": "NoneType",
        "maxSimulationStreak": "int",
        "operatorAvg": "float",
        "operatorCount": "int",
        "pyramidCount": "int",
        "quarter": "dict"
      }
    ],
    "previous": {
      "alphaCount": "int",
      "combinedAlphaPerformance": "float",
      "combinedOsmosisPerformance": "float",
      "combinedPowerPoolAlphaPerformance": "float",
      "combinedSelectedAlphaPerformance": "float",
      "communityActivity": "float",
      "extras": [],
      "fieldAvg": "float",
      "fieldCount": "int",
      "geniusLevel": "str",
      "level": "str",
      "maxSimulationStreak": "int",
      "operatorAvg": "float",
      "operatorCount": "int",
      "pyramidCount": "int",
      "quarter": {
        "endDate": "str",
        "name": "str",
        "startDate": "str"
      }
    }
  }
}
```

### `GET /users/self/consultant/tutorial/summary`

- Status: `tested`
- Tested path: `/users/self/consultant/tutorial/summary`
- HTTP: `200 OK`
- Elapsed: `302 ms`
- Content-Type: `application/json`
- Allow: `GET, PATCH, HEAD, OPTIONS`

```json
{
  "active": "bool",
  "currentStep": "int",
  "status": "str",
  "steps": [
    {
      "answer": "null",
      "hint": "null",
      "id": "int",
      "name": "str",
      "requirements": "null",
      "slug": "str",
      "status": "str",
      "task": "null",
      "visited": "bool"
    }
  ]
}
```

### `PATCH /users/self/consultant/tutorial/summary`

- Status: `skipped_mutating`
- Tested path: `/users/self/consultant/tutorial/summary`
- Reason: PATCH may mutate remote state; not executed by inventory test.

### `GET /users/self/messages`

- Status: `tested`
- Tested path: `/users/self/messages`
- HTTP: `200 OK`
- Elapsed: `500 ms`
- Content-Type: `application/json`
- Allow: `GET, HEAD, OPTIONS`

```json
{
  "count": "int",
  "next": "str",
  "previous": "null",
  "results": [
    {
      "dateCreated": "str",
      "description": "str",
      "id": "str",
      "read": "bool",
      "tags": [],
      "title": "str",
      "type": "str"
    }
  ]
}
```

### `GET /users/self/messages/summary`

- Status: `tested`
- Tested path: `/users/self/messages/summary`
- HTTP: `200 OK`
- Elapsed: `263 ms`
- Content-Type: `application/json`
- Allow: `GET, PATCH, HEAD, OPTIONS`

```json
{
  "announcement": {
    "count": "int",
    "read": "int",
    "unread": "int"
  },
  "notification": {
    "count": "int",
    "read": "int",
    "unread": "int"
  }
}
```

### `GET /users/self/pyramid/alphas`

- Status: `tested`
- Tested path: `/users/self/pyramid/alphas`
- HTTP: `404 Not Found`
- Elapsed: `257 ms`
- Content-Type: `application/json`

```json
{
  "detail": "str"
}
```

### `GET /users/self/teams`

- Status: `tested`
- Tested path: `/users/self/teams`
- HTTP: `200 OK`
- Elapsed: `256 ms`
- Content-Type: `application/json`
- Allow: `GET, HEAD, OPTIONS`

```json
{
  "count": "int",
  "next": "null",
  "previous": "null",
  "results": []
}
```

### `GET /users/self/tutorial/steps`

- Status: `tested`
- Tested path: `/users/self/tutorial/steps`
- HTTP: `200 OK`
- Elapsed: `271 ms`
- Content-Type: `application/json`
- Allow: `GET, HEAD, OPTIONS`

```json
[
  {
    "answer": "str",
    "hint": "str",
    "name": "str",
    "slug": "str",
    "stepIndex": "int",
    "task": "str"
  }
]
```

### `GET /users/self/tutorial/summary`

- Status: `tested`
- Tested path: `/users/self/tutorial/summary`
- HTTP: `200 OK`
- Elapsed: `271 ms`
- Content-Type: `application/json`
- Allow: `GET, POST, PATCH, HEAD, OPTIONS`

```json
{
  "active": "bool",
  "completionDate": "null",
  "currentStep": "null",
  "expireDatetime": "null",
  "expired": "bool",
  "maxUnlockedStep": "null",
  "notificationSlug": "null",
  "startDatetime": "null",
  "status": "null",
  "totalSteps": "int"
}
```

### `GET /users/{user_id}`

- Status: `tested`
- Tested path: `/users/JL40454`
- HTTP: `200 OK`
- Elapsed: `307 ms`
- Content-Type: `application/json`
- Allow: `GET, PUT, PATCH, DELETE, HEAD, OPTIONS`

```json
{
  "address": {
    "city": "str",
    "country": "str",
    "postalCode": "null",
    "state": "null",
    "street": "null"
  },
  "approved": "bool",
  "auxiliary": {
    "campaign": {
      "campaign": "str",
      "content": "str",
      "medium": "str",
      "source": "str",
      "term": "null"
    }
  },
  "dateApproved": "str",
  "dateCreated": "str",
  "dateVerified": "str",
  "education": {
    "degree": "str",
    "gpa": "float",
    "graduationYear": "int",
    "major": "str",
    "maxGPA": "float",
    "stem": "bool",
    "university": "str"
  },
  "email": "str",
  "employment": "null",
  "firstName": "str",
  "fullName": "str",
  "gender": "str",
  "geniusLevel": "str",
  "id": "str",
  "image": {
    "url": "str"
  },
  "lastName": "str",
  "onboarding": {
    "status": "str"
  },
  "recruitment": {
    "codingProficiency": "str",
    "englishProficiency": "str",
    "roleInterest": [
      "str"
    ]
  },
  "resume": {
    "dateCreated": "str"
  },
  "settings": {
    "allowTracking": "bool",
    "client": {},
    "communication": {
      "allowSMS": "bool"
    },
    "privacy": {
      "image": {
        "moderation": "str",
        "visibility": "str"
      },
      "name": {
        "moderation": "str",
        "visibility": "str"
      }
    }
  },
  "telephone": "str",
  "verified": "bool"
}
```

### `GET /users/{user_id}/achievements`

- Status: `tested`
- Tested path: `/users/JL40454/achievements`
- HTTP: `200 OK`
- Elapsed: `614 ms`
- Content-Type: `application/json`
- Allow: `GET, HEAD, OPTIONS`

```json
[
  {
    "achieved": "str",
    "description": "str",
    "id": "str",
    "name": "str",
    "ratio": "float",
    "total": "int",
    "value": "int"
  }
]
```

### `GET /users/{user_id}/activities`

- Status: `tested`
- Tested path: `/users/JL40454/activities`
- HTTP: `200 OK`
- Elapsed: `263 ms`
- Content-Type: `application/json`
- Allow: `GET, HEAD, OPTIONS`

```json
{
  "count": "int",
  "next": "null",
  "previous": "null",
  "results": [
    {
      "name": "str",
      "title": "str"
    }
  ]
}
```

### `GET /users/{user_id}/activities/diversity`

- Status: `tested`
- Tested path: `/users/JL40454/activities/diversity`
- HTTP: `200 OK`
- Elapsed: `473 ms`
- Content-Type: `application/json`
- Allow: `GET, HEAD, OPTIONS`

```json
{
  "alphas": [
    {
      "alphaCount": "int",
      "dataCategory": {
        "id": "str",
        "name": "str"
      },
      "dataDiversity": {
        "check": "str",
        "limit": "float"
      },
      "delay": "int",
      "region": "str"
    }
  ],
  "count": "int"
}
```

### `OPTIONS /users/{user_id}/alphas`

- Status: `tested`
- Tested path: `/users/JL40454/alphas`
- HTTP: `200 OK`
- Elapsed: `675 ms`
- Content-Type: `application/json`
- Allow: `GET, HEAD, OPTIONS`

```json
{
  "actions": {
    "GET": {
      "author": {
        "label": "str",
        "readOnly": "bool",
        "required": "bool",
        "type": "str"
      },
      "category": {
        "choices": "list",
        "label": "str",
        "readOnly": "bool",
        "required": "bool",
        "type": "str"
      },
      "classifications": {
        "choices": "list",
        "label": "str",
        "readOnly": "bool",
        "required": "bool",
        "type": "str"
      },
      "color": {
        "choices": "list",
        "label": "str",
        "readOnly": "bool",
        "required": "bool",
        "type": "str"
      },
      "combo": {
        "children": "dict",
        "label": "str",
        "readOnly": "bool",
        "required": "bool",
        "type": "str"
      },
      "competitions": {
        "choices": "list",
        "label": "str",
        "readOnly": "bool",
        "required": "bool",
        "type": "str"
      },
      "dateCreated": {
        "label": "str",
        "readOnly": "bool",
        "required": "bool",
        "type": "str"
      },
      "dateModified": {
        "label": "str",
        "readOnly": "bool",
        "required": "bool",
        "type": "str"
      },
      "dateSubmitted": {
        "label": "str",
        "readOnly": "bool",
        "required": "bool",
        "type": "str"
      },
      "favorite": {
        "label": "str",
        "readOnly": "bool",
        "required": "bool",
        "type": "str"
      },
      "grade": {
        "choices": "list",
        "label": "str",
        "readOnly": "bool",
        "required": "bool",
        "type": "str"
      },
      "hidden": {
        "label": "str",
        "readOnly": "bool",
        "required": "bool",
        "type": "str"
      },
      "id": {
        "label": "str",
        "readOnly": "bool",
        "required": "bool",
        "type": "str"
      },
      "is": {
        "child": "dict",
        "label": "str",
        "readOnly": "bool",
        "required": "bool",
        "type": "str"
      },
      "name": {
        "label": "str",
        "readOnly": "bool",
        "required": "bool",
        "type": "str"
      },
      "origin": {
        "label": "str",
        "readOnly": "bool",
        "required": "bool",
        "type": "str"
      },
      "os": {
        "child": "dict",
        "label": "str",
        "readOnly": "bool",
        "required": "bool",
        "type": "str"
      },
      "osmosisPoints": {
        "label": "str",
        "maxValue": "int",
        "minValue": "int",
        "readOnly": "bool",
        "required": "bool",
        "type": "str"
      },
      "prod": {
        "child": "dict",
        "label": "str",
        "readOnly": "bool",
        "required": "bool",
        "type": "str"
      },
      "pyramidThemes": {
        "choices": "list",
        "label": "str",
        "readOnly": "bool",
        "required": "bool",
        "type": "str"
      },
      "pyramids": {
        "choices": "list",
        "label": "str",
        "readOnly": "bool",
        "required": "bool",
        "type": "str"
      },
      "regular": {
        "children": "dict",
        "label": "str",
        "readOnly": "bool",
        "required": "bool",
        "type": "str"
      },
      "selection": {
        "children": "dict",
        "label": "str",
        "readOnly": "bool",
        "required": "bool",
        "type": "str"
      },
      "settings": {
        "children": "dict",
        "label": "str",
        "readOnly": "bool",
        "required": "bool",
        "type": "str"
      },
      "stage": {
        "choices": "list",
        "label": "str",
        "readOnly": "bool",
        "required": "bool",
        "type": "str"
      },
      "status": {
        "choices": "list",
        "label": "str",
        "readOnly": "bool",
        "required": "bool",
        "type": "str"
      },
      "tags": {
        "child": "dict",
        "choices": "list",
        "label": "str",
        "readOnly": "bool",
        "required": "bool",
        "type": "str"
      },
      "team": {
        "choices": "list",
        "label": "str",
        "readOnly": "bool",
        "required": "bool",
        "type": "str"
      },
      "test": {
        "child": "dict",
        "label": "str",
        "readOnly": "bool",
        "required": "bool",
        "type": "str"
      },
      "themes": {
        "choices": "list",
        "label": "str",
        "readOnly": "bool",
        "required": "bool",
        "type": "str"
      },
      "train": {
        "child": "dict",
        "label": "str",
        "readOnly": "bool",
        "required": "bool",
        "type": "str"
      },
      "type": {
        "choices": "list",
        "label": "str",
        "readOnly": "bool",
        "required": "bool",
        "type": "str"
      }
    }
  }
}
```

### `GET /users/{user_id}/competitions`

- Status: `tested`
- Tested path: `/users/JL40454/competitions`
- HTTP: `200 OK`
- Elapsed: `801 ms`
- Content-Type: `application/json`
- Allow: `GET, HEAD, OPTIONS`

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

### `GET /users/{user_id}/settings/simulation`

- Status: `tested`
- Tested path: `/users/JL40454/settings/simulation`
- HTTP: `200 OK`
- Elapsed: `262 ms`
- Content-Type: `application/json`
- Allow: `GET, POST, HEAD, OPTIONS`

```json
{
  "componentActivation": "str",
  "decay": "int",
  "delay": "int",
  "instrumentType": "str",
  "language": "str",
  "lookback": "int",
  "maxPosition": "str",
  "maxTrade": "str",
  "neutralization": "str",
  "region": "str",
  "selectionHandling": "str",
  "selectionLimit": "int",
  "testPeriod": "str",
  "truncation": "float",
  "universe": "str",
  "visualization": "bool"
}
```

### `GET /video-courses`

- Status: `tested`
- Tested path: `/video-courses`
- HTTP: `200 OK`
- Elapsed: `421 ms`
- Content-Type: `application/json`
- Allow: `GET, HEAD, OPTIONS`

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
