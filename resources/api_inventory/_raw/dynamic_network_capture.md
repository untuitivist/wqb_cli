# Platform Dynamic Network Capture

- Generated at: `2026-05-18T16:44:06.521712+00:00`
- Routes visited: `14`
- Unique API method/path pairs: `41`
- Safety: `Only passive page navigation was performed; no buttons were clicked and no mutating API calls were initiated by this script.`

## Routes

- `https://platform.worldquantbrain.com/` -> `200`
- `https://platform.worldquantbrain.com/data` -> `200`
- `https://platform.worldquantbrain.com/data/data-sets` -> `200`
- `https://platform.worldquantbrain.com/data/data-fields` -> `200`
- `https://platform.worldquantbrain.com/operators` -> `200`
- `https://platform.worldquantbrain.com/alpha` -> `200`
- `https://platform.worldquantbrain.com/alphas` -> `200`
- `https://platform.worldquantbrain.com/simulations` -> `200`
- `https://platform.worldquantbrain.com/consultant` -> `200`
- `https://platform.worldquantbrain.com/competitions` -> `200`
- `https://platform.worldquantbrain.com/events` -> `200`
- `https://platform.worldquantbrain.com/tutorials` -> `200`
- `https://platform.worldquantbrain.com/messages` -> `200`
- `https://platform.worldquantbrain.com/settings` -> `200`

## Observed API Calls

### `GET /achievements/ALPHA_PERF_EXCELLENT/icon`

- Seen count: `1`
- Query keys: ``
- Status codes: `200`

### `GET /achievements/ALPHA_PERF_GOOD/icon`

- Seen count: `1`
- Query keys: ``
- Status codes: `200`

### `GET /achievements/ALPHA_PERF_SPECTACULAR/icon`

- Seen count: `1`
- Query keys: ``
- Status codes: `200`

### `GET /achievements/CONSULTANT_SUBMIT/icon`

- Seen count: `1`
- Query keys: ``
- Status codes: `200`

### `GET /achievements/SIMULATION_100/icon`

- Seen count: `1`
- Query keys: ``
- Status codes: `200`

### `GET /achievements/SIMULATION_20/icon`

- Seen count: `1`
- Query keys: ``
- Status codes: `200`

### `GET /achievements/SUBMIT_1/icon`

- Seen count: `1`
- Query keys: ``
- Status codes: `200`

### `GET /achievements/SUBMIT_10/icon`

- Seen count: `1`
- Query keys: ``
- Status codes: `200`

### `GET /achievements/SUPER_ALPHA/icon`

- Seen count: `1`
- Query keys: ``
- Status codes: `200`

### `GET /authentication`

- Seen count: `14`
- Query keys: ``
- Status codes: `200`
- Response shape sample:
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

### `GET /captcha`

- Seen count: `14`
- Query keys: ``
- Status codes: `200`
- Response shape sample:
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

- Seen count: `1`
- Query keys: ``
- Status codes: `200`
- Response shape sample:
```json
[
  {
    "id": "str",
    "name": "str"
  }
]
```

### `GET /competition-levels/none/icon`

- Seen count: `1`
- Query keys: ``
- Status codes: `200`

### `GET /competitions`

- Seen count: `1`
- Query keys: `limit, offset`
- Status codes: `200`
- Response shape sample:
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

### `GET /configuration`

- Seen count: `14`
- Query keys: ``
- Status codes: `200`
- Response shape sample:
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

### `GET /consultant/boards/leader`

- Seen count: `14`
- Query keys: `user`
- Status codes: `200`
- Response shape sample:
```json
{
  "count": "int",
  "next": "null",
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

### `GET /data-categories`

- Seen count: `3`
- Query keys: ``
- Status codes: `200`
- Response shape sample:
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

- Seen count: `9`
- Query keys: `delay, instrumentType, limit, offset, region, universe`
- Status codes: `200`
- Response shape sample:
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

### `GET /data-sets`

- Seen count: `2`
- Query keys: `delay, instrumentType, limit, offset, region, theme, universe`
- Status codes: `200`
- Response shape sample:
```json
{
  "count": "int",
  "results": []
}
```

### `POST /errors/api/2/envelope/`

- Seen count: `61`
- Query keys: `sentry_client, sentry_key, sentry_version`
- Status codes: `200`
- Request body shape:
```json
{
  "raw_body": "non-json",
  "length": 463
}
```
- Response shape sample:
```json
{}
```

### `GET /events`

- Seen count: `2`
- Query keys: `limit, order, start>`
- Status codes: `200`
- Response shape sample:
```json
{
  "count": "int",
  "next": "null",
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

- Seen count: `1`
- Query keys: ``
- Status codes: `200`
- Response shape sample:
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

### `GET /operators`

- Seen count: `15`
- Query keys: ``
- Status codes: `200`
- Response shape sample:
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

### `OPTIONS /simulations`

- Seen count: `22`
- Query keys: ``
- Status codes: `200`
- Response shape sample:
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

### `GET /suggest/fields`

- Seen count: `8`
- Query keys: ``
- Status codes: `200`
- Response shape sample:
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

### `GET /tutorial/exclusive-events-and-support-for-consultants`

- Seen count: `8`
- Query keys: ``
- Status codes: `200`
- Response shape sample:
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

### `GET /users/JL40454`

- Seen count: `14`
- Query keys: ``
- Status codes: `200`
- Response shape sample:
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

### `GET /users/JL40454/achievements`

- Seen count: `1`
- Query keys: ``
- Status codes: `200`
- Response shape sample:
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

### `OPTIONS /users/JL40454/alphas`

- Seen count: `14`
- Query keys: ``
- Status codes: `200`
- Response shape sample:
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

### `GET /users/JL40454/competitions`

- Seen count: `14`
- Query keys: ``
- Status codes: `200`
- Response shape sample:
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

### `GET /users/JL40454/settings/simulation`

- Seen count: `14`
- Query keys: ``
- Status codes: `200`
- Response shape sample:
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

### `GET /users/self/achievements`

- Seen count: `1`
- Query keys: ``
- Status codes: `200`
- Response shape sample:
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

### `GET /users/self/activities/simulations`

- Seen count: `8`
- Query keys: `date>`
- Status codes: `200`
- Response shape sample:
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

- Seen count: `14`
- Query keys: ``
- Status codes: `200`
- Response shape sample:
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

### `GET /users/self/alphas/summary`

- Seen count: `1`
- Query keys: ``
- Status codes: `200`
- Response shape sample:
```json
{
  "active": "int",
  "decommissioned": "int",
  "unsubmitted": "int"
}
```

### `GET /users/self/consultant/summary`

- Seen count: `1`
- Query keys: ``
- Status codes: `200`
- Response shape sample:
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

- Seen count: `22`
- Query keys: ``
- Status codes: `200`
- Response shape sample:
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

- Seen count: `8`
- Query keys: ``
- Status codes: `200`
- Request body shape:
```json
{
  "active": "bool"
}
```

### `GET /users/self/messages`

- Seen count: `16`
- Query keys: `limit, order, type`
- Status codes: `200`
- Response shape sample:
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

- Seen count: `14`
- Query keys: ``
- Status codes: `200`
- Response shape sample:
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

### `GET /users/self/teams`

- Seen count: `42`
- Query keys: `members.self.status, order, status`
- Status codes: `200`
- Response shape sample:
```json
{
  "count": "int",
  "next": "null",
  "previous": "null",
  "results": []
}
```
