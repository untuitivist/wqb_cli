# `/consultant/boards/leader`

- URL template: `https://api.worldquantbrain.com/consultant/boards/leader`
- Methods: `GET`
- Sources: `observed_platform, platform_dynamic_capture`
- Safe probe: `True`
- Description: Consultant leaderboard.
- Params: `{"user": "observed query parameter"}`

## Probe

- Probe URL: `https://api.worldquantbrain.com/consultant/boards/leader`
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
      "user": "str",
      "weightFactor": "float",
      "valueFactor": "float",
      "dailyOsmosisRank": "float",
      "dataFieldsUsed": "int",
      "submissionsCount": "int",
      "meanProdCorrelation": "float",
      "meanSelfCorrelation": "float",
      "superAlphaSubmissionsCount": "int",
      "superAlphaMeanProdCorrelation": "float",
      "superAlphaMeanSelfCorrelation": "float",
      "university": "str",
      "country": "str"
    }
  ]
}
```

## Dynamic Capture

### `GET /consultant/boards/leader`

- Seen count: `14`
- Status codes: `200`
- Query keys: `user`
- Content types: `application/json`

#### Response Shape

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

## Endpoint Tests

### `GET /consultant/boards/leader`

- Status: `tested`
- Tested path: `/consultant/boards/leader`
- HTTP: `200 OK`
- Elapsed: `378 ms`
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
