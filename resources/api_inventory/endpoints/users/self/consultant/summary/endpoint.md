# `/users/self/consultant/summary`

- URL template: `https://api.worldquantbrain.com/users/self/consultant/summary`
- Methods: `GET`
- Sources: `platform_dynamic_capture, platform_frontend`
- Safe probe: `True`
- Description: Current consultant performance summary.

## Probe

- Probe URL: `https://api.worldquantbrain.com/users/self/consultant/summary`
- Allowed methods: `GET, HEAD, OPTIONS`
- Status: `200 OK`
- Usable GET: `True`

### Response Shape

```json
{
  "performance": {
    "currentLevel": "str",
    "bestLevel": "str",
    "currentQuarter": {
      "name": "str",
      "startDate": "str",
      "endDate": "str"
    },
    "current": {
      "level": "NoneType",
      "geniusLevel": "str",
      "quarter": {
        "name": "...",
        "startDate": "...",
        "endDate": "..."
      },
      "alphaCount": "int",
      "pyramidCount": "int",
      "combinedSelectedAlphaPerformance": "float",
      "combinedAlphaPerformance": "float",
      "operatorCount": "int",
      "operatorAvg": "float",
      "fieldCount": "int",
      "fieldAvg": "float",
      "communityActivity": "float",
      "maxSimulationStreak": "int",
      "extras": [],
      "combinedPowerPoolAlphaPerformance": "float",
      "combinedOsmosisPerformance": "float"
    },
    "previous": {
      "level": "str",
      "geniusLevel": "str",
      "quarter": {
        "name": "...",
        "startDate": "...",
        "endDate": "..."
      },
      "alphaCount": "int",
      "pyramidCount": "int",
      "combinedSelectedAlphaPerformance": "float",
      "combinedAlphaPerformance": "float",
      "operatorCount": "int",
      "operatorAvg": "float",
      "fieldCount": "int",
      "fieldAvg": "float",
      "communityActivity": "float",
      "maxSimulationStreak": "int",
      "extras": [],
      "combinedPowerPoolAlphaPerformance": "float",
      "combinedOsmosisPerformance": "float"
    },
    "history": [
      {
        "level": "...",
        "geniusLevel": "...",
        "quarter": "...",
        "alphaCount": "...",
        "pyramidCount": "...",
        "combinedSelectedAlphaPerformance": "...",
        "combinedAlphaPerformance": "...",
        "operatorCount": "...",
        "operatorAvg": "...",
        "fieldCount": "...",
        "fieldAvg": "...",
        "communityActivity": "...",
        "maxSimulationStreak": "...",
        "extras": "..."
      }
    ]
  },
  "leaderboard": {
    "rank": "int",
    "user": "str",
    "extras": [],
    "geniusLevel": "str",
    "bestLevel": "str",
    "alphaCount": "int",
    "pyramidCount": "int",
    "combinedAlphaPerformance": "float",
    "combinedPowerPoolAlphaPerformance": "float",
    "combinedSelectedAlphaPerformance": "float",
    "combinedOsmosisPerformance": "float",
    "operatorCount": "int",
    "operatorAvg": "float",
    "fieldCount": "int",
    "fieldAvg": "float",
    "communityActivity": "float",
    "maxSimulationStreak": "int",
    "country": "str"
  },
  "osmosis": [
    {
      "region": "str",
      "delay": "int",
      "pointsAllocated": "int",
      "alphas": "int"
    }
  ]
}
```

## Dynamic Capture

### `GET /users/self/consultant/summary`

- Seen count: `1`
- Status codes: `200`
- Query keys: ``
- Content types: `application/json`

#### Response Shape

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

## Endpoint Tests

### `GET /users/self/consultant/summary`

- Status: `tested`
- Tested path: `/users/self/consultant/summary`
- HTTP: `200 OK`
- Elapsed: `2442 ms`
- Content-Type: `application/json`
- Allow: `GET, HEAD, OPTIONS`

#### Tested Response Shape

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
