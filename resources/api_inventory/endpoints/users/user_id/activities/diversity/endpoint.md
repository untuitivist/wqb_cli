# `/users/{user_id}/activities/diversity`

- URL template: `https://api.worldquantbrain.com/users/{user_id}/activities/diversity`
- Methods: `GET`
- Sources: `official_doc_snippet`
- Safe probe: `False`
- Description: 按 Region、Delay、Data Category 返回 alpha 提交分布。

## Probe

- Skipped/Error: `Official-only entry; no safe sample probe generated.`

## Official Notes

```json
{
  "summary": "按 Region、Delay、Data Category 返回 alpha 提交分布。",
  "methods": {
    "GET": {
      "params": {
        "grouping": "region,delay,dataCategory"
      },
      "response": {
        "alphas": "array of alphaCount, delay, region, dataCategory",
        "count": "total alpha count"
      }
    }
  }
}
```

## Endpoint Tests

### `GET /users/{user_id}/activities/diversity`

- Status: `tested`
- Tested path: `/users/JL40454/activities/diversity`
- HTTP: `200 OK`
- Elapsed: `473 ms`
- Content-Type: `application/json`
- Allow: `GET, HEAD, OPTIONS`

#### Tested Response Shape

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
