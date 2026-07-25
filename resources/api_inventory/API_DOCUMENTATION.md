# WorldQuant BRAIN API Documentation

- Base URL: `https://api.worldquantbrain.com`
- Generated at: `2026-07-16T08:57:52+00:00`
- Endpoint count: `109`
- Method case count: `134`
- 测试边界：`GET/HEAD/OPTIONS` 实际请求；`POST/PATCH/PUT/DELETE` 只记录为危险动作，不执行。
- 响应内容只记录结构，不记录 cookie、JWT 或完整业务数据。

## Test Summary

- Executed safe cases: `110`
- Tested cases: `110`
- Request errors: `0`
- Skipped mutating cases: `24`
- Skipped missing sample cases: `0`
- HTTP 2xx/3xx: `71`
- HTTP 4xx/5xx: `39`

## Method Coverage

- `DELETE`: `1`
- `GET`: `106`
- `HEAD`: `1`
- `OPTIONS`: `3`
- `PATCH`: `3`
- `POST`: `19`
- `PUT`: `1`

## HTTP Status Coverage

- `200`: `68`
- `302`: `3`
- `400`: `3`
- `404`: `24`
- `405`: `12`

## Source Coverage

- `observed_platform`: `29`
- `official_doc_snippet`: `2`
- `platform_dynamic_capture`: `31`
- `platform_frontend`: `65`
- `rocky-d/wqb`: `15`

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

## URL Tree

- `/achievements` -> `endpoints/achievements/endpoint.md`
- `/achievements/{achievement_id}/icon` -> `endpoints/achievements/achievement_id/icon/endpoint.md`
- `/agreements` -> `endpoints/agreements/endpoint.md`
- `/alphas` -> `endpoints/alphas/endpoint.md`
- `/alphas/distribution` -> `endpoints/alphas/distribution/endpoint.md`
- `/alphas/lists` -> `endpoints/alphas/lists/endpoint.md`
- `/alphas/sample-alpha-id-walkthrough` -> `endpoints/alphas/sample-alpha-id-walkthrough/endpoint.md`
- `/alphas/super-selection` -> `endpoints/alphas/super-selection/endpoint.md`
- `/alphas/unsubmitted` -> `endpoints/alphas/unsubmitted/endpoint.md`
- `/alphas/{alpha_id}` -> `endpoints/alphas/alpha_id/endpoint.md`
- `/alphas/{alpha_id}/alphas` -> `endpoints/alphas/alpha_id/alphas/endpoint.md`
- `/alphas/{alpha_id}/check` -> `endpoints/alphas/alpha_id/check/endpoint.md`
- `/alphas/{alpha_id}/correlations` -> `endpoints/alphas/alpha_id/correlations/endpoint.md`
- `/alphas/{alpha_id}/correlations/power-pool` -> `endpoints/alphas/alpha_id/correlations/power-pool/endpoint.md`
- `/alphas/{alpha_id}/correlations/prod` -> `endpoints/alphas/alpha_id/correlations/prod/endpoint.md`
- `/alphas/{alpha_id}/correlations/self` -> `endpoints/alphas/alpha_id/correlations/self/endpoint.md`
- `/alphas/{alpha_id}/performance-comparison` -> `endpoints/alphas/alpha_id/performance-comparison/endpoint.md`
- `/alphas/{alpha_id}/recordsets` -> `endpoints/alphas/alpha_id/recordsets/endpoint.md`
- `/alphas/{alpha_id}/recordsets/pnl` -> `endpoints/alphas/alpha_id/recordsets/pnl/endpoint.md`
- `/alphas/{alpha_id}/recordsets/sharpe` -> `endpoints/alphas/alpha_id/recordsets/sharpe/endpoint.md`
- `/alphas/{alpha_id}/recordsets/yearly-stats` -> `endpoints/alphas/alpha_id/recordsets/yearly-stats/endpoint.md`
- `/alphas/{alpha_id}/recordsets/{record_set_name}` -> `endpoints/alphas/alpha_id/recordsets/record_set_name/endpoint.md`
- `/alphas/{alpha_id}/submit` -> `endpoints/alphas/alpha_id/submit/endpoint.md`
- `/authentication` -> `endpoints/authentication/endpoint.md`
- `/authentication/brainlabs` -> `endpoints/authentication/brainlabs/endpoint.md`
- `/authentication/persona` -> `endpoints/authentication/persona/endpoint.md`
- `/authentication/support` -> `endpoints/authentication/support/endpoint.md`
- `/authentication/workday` -> `endpoints/authentication/workday/endpoint.md`
- `/captcha` -> `endpoints/captcha/endpoint.md`
- `/competition-levels` -> `endpoints/competition-levels/endpoint.md`
- `/competition-levels/{competition_level_id}/icon` -> `endpoints/competition-levels/competition_level_id/icon/endpoint.md`
- `/competitions` -> `endpoints/competitions/endpoint.md`
- `/competitions/{competition_id}` -> `endpoints/competitions/competition_id/endpoint.md`
- `/competitions/{competition_id}/boards/{board_type}` -> `endpoints/competitions/competition_id/boards/board_type/endpoint.md`
- `/competitions/{competition_id}/agreement` -> `endpoints/competitions/competition_id/agreement/endpoint.md`
- `/competitions/spc/submissions` -> `endpoints/competitions/spc/submissions/endpoint.md`
- `/competitions/spc/submissions/{submission_id}` -> `endpoints/competitions/spc/submissions/submission_id/endpoint.md`
- `/configuration` -> `endpoints/configuration/endpoint.md`
- `/consultant` -> `endpoints/consultant/endpoint.md`
- `/consultant-datasets` -> `endpoints/consultant-datasets/endpoint.md`
- `/consultant-information/consultant-dos-and-donts` -> `endpoints/consultant-information/consultant-dos-and-donts/endpoint.md`
- `/consultant-information/consultant-faqs` -> `endpoints/consultant-information/consultant-faqs/endpoint.md`
- `/consultant-information/osmosis-allocation-guide-consultants` -> `endpoints/consultant-information/osmosis-allocation-guide-consultants/endpoint.md`
- `/consultant-information/visualization-tool` -> `endpoints/consultant-information/visualization-tool/endpoint.md`
- `/consultant-program` -> `endpoints/consultant-program/endpoint.md`
- `/consultant-program/{language}` -> `endpoints/consultant-program/language/endpoint.md`
- `/consultant/boards` -> `endpoints/consultant/boards/endpoint.md`
- `/consultant/boards/leader` -> `endpoints/consultant/boards/leader/endpoint.md`
- `/consultant/boards/spc` -> `endpoints/consultant/boards/spc/endpoint.md`
- `/consultant/boards/{board_type}` -> `endpoints/consultant/boards/board_type/endpoint.md`
- `/consultant/summary` -> `endpoints/consultant/summary/endpoint.md`
- `/data-categories` -> `endpoints/data-categories/endpoint.md`
- `/data-fields` -> `endpoints/data-fields/endpoint.md`
- `/data-fields/summary` -> `endpoints/data-fields/summary/endpoint.md`
- `/data-fields/{field_id}` -> `endpoints/data-fields/field_id/endpoint.md`
- `/data-sets` -> `endpoints/data-sets/endpoint.md`
- `/data-sets/search` -> `endpoints/data-sets/search/endpoint.md`
- `/data-sets/{dataset_id}` -> `endpoints/data-sets/dataset_id/endpoint.md`
- `/errors/api/2/envelope` -> `endpoints/errors/api/2/envelope/endpoint.md`
- `/events` -> `endpoints/events/endpoint.md`
- `/events/{event_id}` -> `endpoints/events/event_id/endpoint.md`
- `/messages` -> `endpoints/messages/endpoint.md`
- `/operators` -> `endpoints/operators/endpoint.md`
- `/search` -> `endpoints/search/endpoint.md`
- `/simulations` -> `endpoints/simulations/endpoint.md`
- `/simulations/super-selection` -> `endpoints/simulations/super-selection/endpoint.md`
- `/simulations/{simulation_id}` -> `endpoints/simulations/simulation_id/endpoint.md`
- `/suggest/examples` -> `endpoints/suggest/examples/endpoint.md`
- `/suggest/expression` -> `endpoints/suggest/expression/endpoint.md`
- `/suggest/fastexpr` -> `endpoints/suggest/fastexpr/endpoint.md`
- `/suggest/fields` -> `endpoints/suggest/fields/endpoint.md`
- `/tags` -> `endpoints/tags/endpoint.md`
- `/teams` -> `endpoints/teams/endpoint.md`
- `/tutorial-pages` -> `endpoints/tutorial-pages/endpoint.md`
- `/tutorial-pages/{page_id}` -> `endpoints/tutorial-pages/page_id/endpoint.md`
- `/tutorial/{tutorial_slug}` -> `endpoints/tutorial/tutorial_slug/endpoint.md`
- `/tutorials` -> `endpoints/tutorials/endpoint.md`
- `/user/email/change` -> `endpoints/user/email/change/endpoint.md`
- `/user/email/reverify` -> `endpoints/user/email/reverify/endpoint.md`
- `/user/email/verify` -> `endpoints/user/email/verify/endpoint.md`
- `/user/password/change` -> `endpoints/user/password/change/endpoint.md`
- `/user/password/forgot` -> `endpoints/user/password/forgot/endpoint.md`
- `/user/password/reset` -> `endpoints/user/password/reset/endpoint.md`
- `/user/token` -> `endpoints/user/token/endpoint.md`
- `/users` -> `endpoints/users/endpoint.md`
- `/users/self` -> `endpoints/users/self/endpoint.md`
- `/users/self/achievements` -> `endpoints/users/self/achievements/endpoint.md`
- `/users/self/activities/pyramid-alphas` -> `endpoints/users/self/activities/pyramid-alphas/endpoint.md`
- `/users/self/activities/pyramid-multipliers` -> `endpoints/users/self/activities/pyramid-multipliers/endpoint.md`
- `/users/self/activities/simulations` -> `endpoints/users/self/activities/simulations/endpoint.md`
- `/users/self/agreements` -> `endpoints/users/self/agreements/endpoint.md`
- `/users/self/alphas` -> `endpoints/users/self/alphas/endpoint.md`
- `/users/self/alphas/summary` -> `endpoints/users/self/alphas/summary/endpoint.md`
- `/users/self/consultant/summary` -> `endpoints/users/self/consultant/summary/endpoint.md`
- `/users/self/consultant/tutorial/summary` -> `endpoints/users/self/consultant/tutorial/summary/endpoint.md`
- `/users/self/messages` -> `endpoints/users/self/messages/endpoint.md`
- `/users/self/messages/summary` -> `endpoints/users/self/messages/summary/endpoint.md`
- `/users/self/pyramid/alphas` -> `endpoints/users/self/pyramid/alphas/endpoint.md`
- `/users/self/teams` -> `endpoints/users/self/teams/endpoint.md`
- `/users/self/tutorial/steps` -> `endpoints/users/self/tutorial/steps/endpoint.md`
- `/users/self/tutorial/summary` -> `endpoints/users/self/tutorial/summary/endpoint.md`
- `/users/{user_id}` -> `endpoints/users/user_id/endpoint.md`
- `/users/{user_id}/achievements` -> `endpoints/users/user_id/achievements/endpoint.md`
- `/users/{user_id}/activities` -> `endpoints/users/user_id/activities/endpoint.md`
- `/users/{user_id}/activities/diversity` -> `endpoints/users/user_id/activities/diversity/endpoint.md`
- `/users/{user_id}/alphas` -> `endpoints/users/user_id/alphas/endpoint.md`
- `/users/{user_id}/competitions` -> `endpoints/users/user_id/competitions/endpoint.md`
- `/users/{user_id}/settings/simulation` -> `endpoints/users/user_id/settings/simulation/endpoint.md`
- `/video-courses` -> `endpoints/video-courses/endpoint.md`

## Endpoint Details

### `/achievements`

#### `/achievements`

- URL: `https://api.worldquantbrain.com/achievements`
- Methods: `GET`
- Sources: `platform_frontend`
- Description: Achievements. / Discovered from platform frontend bundle.
- Tests:
- `GET` -> `200 OK`, `application/json`

Response shape:

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

#### `/achievements/{achievement_id}/icon`

- URL: `https://api.worldquantbrain.com/achievements/{achievement_id}/icon`
- Methods: `GET`
- Sources: `platform_dynamic_capture`
- Description: Observed by passive platform network capture.
- Tests:
- `GET` -> `200 OK`, `image/svg+xml`

### `/agreements`

#### `/agreements`

- URL: `https://api.worldquantbrain.com/agreements`
- Methods: `GET`
- Sources: `platform_frontend`
- Description: Agreements. / Discovered from platform frontend bundle.
- Tests:
- `GET` -> `405 Method Not Allowed`, `application/json`

Response shape:

```json
{
  "detail": "str"
}
```

### `/alphas`

#### `/alphas`

- URL: `https://api.worldquantbrain.com/alphas`
- Methods: `GET`
- Sources: `platform_frontend, rocky-d/wqb`
- Description: Alpha collection. / Discovered from platform frontend bundle.
- Params: `{"limit": "1..100", "offset": "0..10000", "query": "limit=5"}`
- Tests:
- `GET` -> `405 Method Not Allowed`, `application/json`

Response shape:

```json
{
  "detail": "str"
}
```

#### `/alphas/distribution`

- URL: `https://api.worldquantbrain.com/alphas/distribution`
- Methods: `GET`
- Sources: `platform_frontend`
- Description: Alpha distribution aggregate. / Discovered from platform frontend bundle.
- Tests:
- `GET` -> `404 Not Found`, `application/json`

Response shape:

```json
{
  "detail": "str"
}
```

#### `/alphas/lists`

- URL: `https://api.worldquantbrain.com/alphas/lists`
- Methods: `GET`
- Sources: `platform_frontend`
- Description: Alpha lists. / Discovered from platform frontend bundle.
- Tests:
- `GET` -> `404 Not Found`, `application/json`

Response shape:

```json
{
  "detail": "str"
}
```

#### `/alphas/sample-alpha-id-walkthrough`

- URL: `https://api.worldquantbrain.com/alphas/sample-alpha-id-walkthrough`
- Methods: `GET`
- Sources: `platform_frontend`
- Description: Discovered from platform frontend bundle.
- Tests:
- `GET` -> `404 Not Found`, `application/json`

Response shape:

```json
{
  "detail": "str"
}
```

#### `/alphas/super-selection`

- URL: `https://api.worldquantbrain.com/alphas/super-selection`
- Methods: `GET`
- Sources: `platform_frontend`
- Description: Super selection alpha endpoint. / Discovered from platform frontend bundle.
- Tests:
- `GET` -> `404 Not Found`, `application/json`

Response shape:

```json
{
  "detail": "str"
}
```

#### `/alphas/unsubmitted`

- URL: `https://api.worldquantbrain.com/alphas/unsubmitted`
- Methods: `GET`
- Sources: `platform_frontend`
- Description: Unsubmitted alpha endpoint. / Discovered from platform frontend bundle.
- Tests:
- `GET` -> `404 Not Found`, `application/json`

Response shape:

```json
{
  "detail": "str"
}
```

#### `/alphas/{alpha_id}`

- URL: `https://api.worldquantbrain.com/alphas/{alpha_id}`
- Methods: `GET, PATCH`
- Sources: `platform_frontend, rocky-d/wqb`
- Description: Alpha details or property patch. / Discovered from platform frontend bundle.
- Request body: PATCH updates alpha properties.
- Official notes: `获取 alpha 详情。alpha id 通常来自 simulation 完成结果里的 alpha 字段。`
- Tests:
- `GET` -> `200 OK`, `application/json`
- `PATCH` -> `skipped_mutating`; PATCH may mutate remote state; not executed by inventory test.

Response shape:

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
    "pasteurizatio
...
```

#### `/alphas/{alpha_id}/alphas`

- URL: `https://api.worldquantbrain.com/alphas/{alpha_id}/alphas`
- Methods: `GET`
- Sources: `platform_frontend`
- Description: Discovered from platform frontend bundle.
- Tests:
- `GET` -> `404 Not Found`, `application/json`

Response shape:

```json
{
  "detail": "str"
}
```

#### `/alphas/{alpha_id}/check`

- URL: `https://api.worldquantbrain.com/alphas/{alpha_id}/check`
- Methods: `GET`
- Sources: `rocky-d/wqb`
- Description: Alpha simulation check.
- Tests:
- `GET` -> `200 OK`, `application/json`

Response shape:

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

#### `/alphas/{alpha_id}/correlations`

- URL: `https://api.worldquantbrain.com/alphas/{alpha_id}/correlations`
- Methods: `GET`
- Sources: `observed_platform`
- Description: Alpha correlation base endpoint.
- Tests:
- `GET` -> `404 Not Found`, `application/json`

Response shape:

```json
{
  "detail": "str"
}
```

#### `/alphas/{alpha_id}/correlations/power-pool`

- URL: `https://api.worldquantbrain.com/alphas/{alpha_id}/correlations/power-pool`
- Methods: `GET`
- Sources: `observed_platform`
- Description: Power Pool correlation.
- Tests:
- `GET` -> `200 OK`, `application/json`

Response shape:

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

#### `/alphas/{alpha_id}/correlations/prod`

- URL: `https://api.worldquantbrain.com/alphas/{alpha_id}/correlations/prod`
- Methods: `GET`
- Sources: `observed_platform`
- Description: Production correlation.
- Tests:
- `GET` -> `200 OK`, `application/json`

Response shape:

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

#### `/alphas/{alpha_id}/correlations/self`

- URL: `https://api.worldquantbrain.com/alphas/{alpha_id}/correlations/self`
- Methods: `GET`
- Sources: `observed_platform`
- Description: Self correlation.
- Tests:
- `GET` -> `200 OK`, `application/json`

Response shape:

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

#### `/alphas/{alpha_id}/performance-comparison`

- URL: `https://api.worldquantbrain.com/alphas/{alpha_id}/performance-comparison`
- Methods: `GET`
- Sources: `observed_platform`
- Description: Before/after performance comparison.
- Tests:
- `GET` -> `404 Not Found`, `application/json`

Response shape:

```json
{
  "detail": "str"
}
```

#### `/alphas/{alpha_id}/recordsets`

- URL: `https://api.worldquantbrain.com/alphas/{alpha_id}/recordsets`
- Methods: `GET`
- Sources: `observed_platform`
- Description: Alpha recordset index.
- Official notes: `列出 alpha 可用 record sets。`
- Tests:
- `GET` -> `200 OK`, `application/json`

Response shape:

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

#### `/alphas/{alpha_id}/recordsets/pnl`

- URL: `https://api.worldquantbrain.com/alphas/{alpha_id}/recordsets/pnl`
- Methods: `GET`
- Sources: `observed_platform`
- Description: PNL recordset.
- Tests:
- `GET` -> `200 OK`, `application/json`

Response shape:

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

#### `/alphas/{alpha_id}/recordsets/sharpe`

- URL: `https://api.worldquantbrain.com/alphas/{alpha_id}/recordsets/sharpe`
- Methods: `GET`
- Sources: `observed_platform`
- Description: Sharpe recordset.
- Tests:
- `GET` -> `200 OK`, `application/json`

Response shape:

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

#### `/alphas/{alpha_id}/recordsets/yearly-stats`

- URL: `https://api.worldquantbrain.com/alphas/{alpha_id}/recordsets/yearly-stats`
- Methods: `GET`
- Sources: `observed_platform`
- Description: Yearly stats recordset.
- Tests:
- `GET` -> `200 OK`, `application/json`

Response shape:

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

#### `/alphas/{alpha_id}/recordsets/{record_set_name}`

- URL: `https://api.worldquantbrain.com/alphas/{alpha_id}/recordsets/{record_set_name}`
- Methods: `GET`
- Sources: `official_doc_snippet`
- Description: 获取指定 record set。
- Official notes: `获取指定 record set。`
- Tests:
- `GET` -> `200 OK`, `application/json`

Response shape:

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

#### `/alphas/{alpha_id}/submit`

- URL: `https://api.worldquantbrain.com/alphas/{alpha_id}/submit`
- Methods: `POST`
- Sources: `rocky-d/wqb`
- Description: Submit alpha.
- Request body: Submission action. Has side effect.
- Tests:
- `POST` -> `skipped_mutating`; POST may mutate remote state; not executed by inventory test.

### `/authentication`

#### `/authentication`

- URL: `https://api.worldquantbrain.com/authentication`
- Methods: `DELETE, GET, HEAD, POST`
- Sources: `platform_dynamic_capture, platform_frontend, rocky-d/wqb`
- Description: Authentication session endpoint. / Discovered from platform frontend bundle.
- Official notes: `管理当前客户端认证状态。`
- Tests:
- `DELETE` -> `skipped_mutating`; DELETE may mutate remote state; not executed by inventory test.
- `GET` -> `200 OK`, `application/json`
- `HEAD` -> `200 OK`, `application/json`
- `POST` -> `skipped_mutating`; POST may mutate remote state; not executed by inventory test.

Response shape:

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

#### `/authentication/brainlabs`

- URL: `https://api.worldquantbrain.com/authentication/brainlabs`
- Methods: `GET`
- Sources: `platform_frontend`
- Description: Discovered from platform frontend bundle.
- Tests:
- `GET` -> `302 Found`

#### `/authentication/persona`

- URL: `https://api.worldquantbrain.com/authentication/persona`
- Methods: `GET`
- Sources: `platform_frontend`
- Description: Discovered from platform frontend bundle.
- Official notes: `Persona 生物识别/浏览器认证入口。`
- Tests:
- `GET` -> `400 Bad Request`, `application/json`

Response shape:

```json
[
  "str"
]
```

#### `/authentication/support`

- URL: `https://api.worldquantbrain.com/authentication/support`
- Methods: `GET`
- Sources: `platform_frontend`
- Description: Discovered from platform frontend bundle.
- Params: `{"query": "return_to="}`
- Tests:
- `GET` -> `302 Found`

#### `/authentication/workday`

- URL: `https://api.worldquantbrain.com/authentication/workday`
- Methods: `GET`
- Sources: `platform_frontend`
- Description: Discovered from platform frontend bundle.
- Tests:
- `GET` -> `302 Found`

### `/captcha`

#### `/captcha`

- URL: `https://api.worldquantbrain.com/captcha`
- Methods: `GET`
- Sources: `platform_dynamic_capture`
- Description: Observed by passive platform network capture.
- Tests:
- `GET` -> `200 OK`, `application/json`

Response shape:

```json
{
  "algorithm": "str",
  "challenge": "str",
  "maxNumber": "int",
  "salt": "str",
  "signature": "str"
}
```

### `/competition-levels`

#### `/competition-levels`

- URL: `https://api.worldquantbrain.com/competition-levels`
- Methods: `GET`
- Sources: `platform_dynamic_capture, platform_frontend`
- Description: Competition levels. / Discovered from platform frontend bundle.
- Tests:
- `GET` -> `200 OK`, `application/json`

Response shape:

```json
[
  {
    "id": "str",
    "name": "str"
  }
]
```

#### `/competition-levels/{competition_level_id}/icon`

- URL: `https://api.worldquantbrain.com/competition-levels/{competition_level_id}/icon`
- Methods: `GET`
- Sources: `platform_dynamic_capture`
- Description: Observed by passive platform network capture.
- Tests:
- `GET` -> `200 OK`, `image/svg+xml`

### `/competitions`

#### `/competitions`

- URL: `https://api.worldquantbrain.com/competitions`
- Methods: `GET`
- Sources: `observed_platform, platform_dynamic_capture, platform_frontend`
- Description: Competitions list. / Discovered from platform frontend bundle.
- Params: `{"limit": "optional", "offset": "optional"}`
- Tests:
- `GET` -> `200 OK`, `application/json`

Response shape:

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

#### `/competitions/{competition_id}`

- URL: `https://api.worldquantbrain.com/competitions/{competition_id}`
- Methods: `GET`
- Sources: `observed_platform`
- Description: Competition details.
- Tests:
- `GET` -> `200 OK`, `application/json`

Response shape:

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

#### `/competitions/{competition_id}/agreement`

- URL: `https://api.worldquantbrain.com/competitions/{competition_id}/agreement`
- Methods: `GET, POST`
- Sources: `observed_platform`
- Description: Competition agreement.
- Request body: POST may accept agreement.
- Tests:
- `GET` -> `200 OK`, `application/json`
- `POST` -> `skipped_mutating`; POST may mutate remote state; not executed by inventory test.

Response shape:

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

### `/configuration`

#### `/configuration`

- URL: `https://api.worldquantbrain.com/configuration`
- Methods: `GET`
- Sources: `platform_dynamic_capture, platform_frontend`
- Description: Platform configuration. / Discovered from platform frontend bundle.
- Tests:
- `GET` -> `200 OK`, `application/json`

Response shape:

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

### `/consultant`

#### `/consultant`

- URL: `https://api.worldquantbrain.com/consultant`
- Methods: `GET`
- Sources: `platform_frontend`
- Description: Consultant landing endpoint. / Discovered from platform frontend bundle.
- Tests:
- `GET` -> `404 Not Found`, `application/json`

Response shape:

```json
{
  "detail": "str"
}
```

#### `/consultant/boards`

- URL: `https://api.worldquantbrain.com/consultant/boards`
- Methods: `GET`
- Sources: `platform_frontend`
- Description: Consultant boards. / Discovered from platform frontend bundle.
- Tests:
- `GET` -> `404 Not Found`, `application/json`

Response shape:

```json
{
  "detail": "str"
}
```

#### `/consultant/boards/leader`

- URL: `https://api.worldquantbrain.com/consultant/boards/leader`
- Methods: `GET`
- Sources: `observed_platform, platform_dynamic_capture`
- Description: Consultant leaderboard.
- Params: `{"user": "observed query parameter"}`
- Tests:
- `GET` -> `200 OK`, `application/json`

Response shape:

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

#### `/consultant/summary`

- URL: `https://api.worldquantbrain.com/consultant/summary`
- Methods: `GET`
- Sources: `platform_frontend`
- Description: Consultant summary endpoint observed in frontend. / Discovered from platform frontend bundle.
- Tests:
- `GET` -> `404 Not Found`, `application/json`

Response shape:

```json
{
  "detail": "str"
}
```

### `/consultant-datasets`

#### `/consultant-datasets`

- URL: `https://api.worldquantbrain.com/consultant-datasets`
- Methods: `GET`
- Sources: `platform_frontend`
- Description: Consultant datasets. / Discovered from platform frontend bundle.
- Tests:
- `GET` -> `404 Not Found`, `application/json`

Response shape:

```json
{
  "detail": "str"
}
```

### `/consultant-information`

#### `/consultant-information/consultant-dos-and-donts`

- URL: `https://api.worldquantbrain.com/consultant-information/consultant-dos-and-donts`
- Methods: `GET`
- Sources: `platform_frontend`
- Description: Consultant information article. / Discovered from platform frontend bundle.
- Tests:
- `GET` -> `404 Not Found`, `application/json`

Response shape:

```json
{
  "detail": "str"
}
```

#### `/consultant-information/consultant-faqs`

- URL: `https://api.worldquantbrain.com/consultant-information/consultant-faqs`
- Methods: `GET`
- Sources: `platform_frontend`
- Description: Consultant FAQ article. / Discovered from platform frontend bundle.
- Tests:
- `GET` -> `404 Not Found`, `application/json`

Response shape:

```json
{
  "detail": "str"
}
```

#### `/consultant-information/osmosis-allocation-guide-consultants`

- URL: `https://api.worldquantbrain.com/consultant-information/osmosis-allocation-guide-consultants`
- Methods: `GET`
- Sources: `platform_frontend`
- Description: Osmosis allocation guide. / Discovered from platform frontend bundle.
- Tests:
- `GET` -> `404 Not Found`, `application/json`

Response shape:

```json
{
  "detail": "str"
}
```

#### `/consultant-information/visualization-tool`

- URL: `https://api.worldquantbrain.com/consultant-information/visualization-tool`
- Methods: `GET`
- Sources: `platform_frontend`
- Description: Visualization tool guide. / Discovered from platform frontend bundle.
- Tests:
- `GET` -> `404 Not Found`, `application/json`

Response shape:

```json
{
  "detail": "str"
}
```

### `/consultant-program`

#### `/consultant-program`

- URL: `https://api.worldquantbrain.com/consultant-program`
- Methods: `GET`
- Sources: `platform_frontend`
- Description: Discovered from platform frontend bundle.
- Tests:
- `GET` -> `404 Not Found`, `application/json`

Response shape:

```json
{
  "detail": "str"
}
```

#### `/consultant-program/{language}`

- URL: `https://api.worldquantbrain.com/consultant-program/{language}`
- Methods: `GET`
- Sources: `platform_frontend`
- Description: Consultant program by language. / Discovered from platform frontend bundle.
- Tests:
- `GET` -> `404 Not Found`, `application/json`

Response shape:

```json
{
  "detail": "str"
}
```

### `/data-categories`

#### `/data-categories`

- URL: `https://api.worldquantbrain.com/data-categories`
- Methods: `GET`
- Sources: `platform_dynamic_capture, platform_frontend, rocky-d/wqb`
- Description: Data categories. / Discovered from platform frontend bundle.
- Tests:
- `GET` -> `200 OK`, `application/json`

Response shape:

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

### `/data-fields`

#### `/data-fields`

- URL: `https://api.worldquantbrain.com/data-fields`
- Methods: `GET`
- Sources: `platform_dynamic_capture, platform_frontend, rocky-d/wqb`
- Description: Data field search. / Discovered from platform frontend bundle.
- Params: `{"dataset.id": "dataset id", "search": "query", "limit": "1..100", "offset": "0..10000", "delay": "observed query parameter", "instrumentType": "observed query parameter", "region": "observed query parameter", "universe": "observed query parameter"}`
- Tests:
- `GET` -> `200 OK`, `application/json`

Response shape:

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

#### `/data-fields/summary`

- URL: `https://api.worldquantbrain.com/data-fields/summary`
- Methods: `GET`
- Sources: `platform_frontend`
- Description: Data field summary aggregate. / Discovered from platform frontend bundle.
- Tests:
- `GET` -> `200 OK`, `application/json`

Response shape:

```json
[
  {
    "id": "str"
  }
]
```

#### `/data-fields/{field_id}`

- URL: `https://api.worldquantbrain.com/data-fields/{field_id}`
- Methods: `GET`
- Sources: `rocky-d/wqb`
- Description: Data field details.
- Tests:
- `GET` -> `200 OK`, `application/json`

Response shape:

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

### `/data-sets`

#### `/data-sets`

- URL: `https://api.worldquantbrain.com/data-sets`
- Methods: `GET`
- Sources: `platform_dynamic_capture, platform_frontend, rocky-d/wqb`
- Description: Data set search. / Discovered from platform frontend bundle.
- Params: `{"instrumentType": "EQUITY", "region": "region", "delay": "delay", "universe": "universe", "limit": "1..100", "offset": "0..10000", "theme": "observed query parameter"}`
- Tests:
- `GET` -> `200 OK`, `application/json`

Response shape:

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

#### `/data-sets/search`

- URL: `https://api.worldquantbrain.com/data-sets/search`
- Methods: `GET, POST`
- Sources: `platform_frontend`
- Description: Dataset search helper. / Discovered from platform frontend bundle.
- Tests:
- `GET` -> `400 Bad Request`, `application/json`
- `POST` -> `skipped_mutating`; POST may mutate remote state; not executed by inventory test.

Response shape:

```json
{
  "detail": "str"
}
```

#### `/data-sets/{dataset_id}`

- URL: `https://api.worldquantbrain.com/data-sets/{dataset_id}`
- Methods: `GET`
- Sources: `rocky-d/wqb`
- Description: Dataset details.
- Tests:
- `GET` -> `200 OK`, `application/json`

Response shape:

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

### `/errors`

#### `/errors/api/2/envelope`

- URL: `https://api.worldquantbrain.com/errors/api/2/envelope`
- Methods: `POST`
- Sources: `platform_dynamic_capture`
- Description: Observed by passive platform network capture.
- Params: `{"sentry_client": "observed query parameter", "sentry_key": "observed query parameter", "sentry_version": "observed query parameter"}`
- Request body: Observed request body shape in dynamic_capture.
- Tests:
- `POST` -> `skipped_mutating`; POST may mutate remote state; not executed by inventory test.

### `/events`

#### `/events`

- URL: `https://api.worldquantbrain.com/events`
- Methods: `GET, OPTIONS`
- Sources: `observed_platform, platform_dynamic_capture, platform_frontend`
- Description: Events list. / Discovered from platform frontend bundle.
- Params: `{"limit": "optional", "offset": "optional", "order": "observed query parameter", "start>": "observed query parameter"}`
- Tests:
- `GET` -> `200 OK`, `application/json`
- `OPTIONS` -> `200 OK`, `application/json`

Response shape:

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

#### `/events/{event_id}`

- URL: `https://api.worldquantbrain.com/events/{event_id}`
- Methods: `GET`
- Sources: `platform_frontend`
- Description: Event details. / Discovered from platform frontend bundle.
- Tests:
- `GET` -> `200 OK`, `application/json`

Response shape:

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

### `/messages`

#### `/messages`

- URL: `https://api.worldquantbrain.com/messages`
- Methods: `GET`
- Sources: `platform_frontend`
- Description: Message collection. / Discovered from platform frontend bundle.
- Tests:
- `GET` -> `404 Not Found`, `application/json`

Response shape:

```json
{
  "detail": "str"
}
```

### `/operators`

#### `/operators`

- URL: `https://api.worldquantbrain.com/operators`
- Methods: `GET`
- Sources: `platform_dynamic_capture, platform_frontend, rocky-d/wqb`
- Description: Operator list/search. / Discovered from platform frontend bundle.
- Params: `{"instrumentType": "optional", "region": "optional", "delay": "optional"}`
- Tests:
- `GET` -> `200 OK`, `application/json`

Response shape:

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

### `/search`

#### `/search`

- URL: `https://api.worldquantbrain.com/search`
- Methods: `GET`
- Sources: `platform_frontend`
- Description: Global search. / Discovered from platform frontend bundle.
- Params: `{"query": "search text"}`
- Tests:
- `GET` -> `400 Bad Request`, `application/json`

Response shape:

```json
{
  "query": [
    "str"
  ]
}
```

### `/simulations`

#### `/simulations`

- URL: `https://api.worldquantbrain.com/simulations`
- Methods: `GET, OPTIONS, POST`
- Sources: `platform_dynamic_capture, platform_frontend, rocky-d/wqb`
- Description: Simulation collection and simulation creation. / Discovered from platform frontend bundle.
- Request body: POST creates simulation. Do not auto-probe POST.
- Official notes: `创建 simulation 或获取 simulation endpoint 的 OPTIONS schema。`
- Tests:
- `GET` -> `405 Method Not Allowed`, `application/json`
- `OPTIONS` -> `200 OK`, `application/json`
- `POST` -> `skipped_mutating`; POST may mutate remote state; not executed by inventory test.

Response shape:

```json
{
  "detail": "str"
}
```

#### `/simulations/super-selection`

- URL: `https://api.worldquantbrain.com/simulations/super-selection`
- Methods: `GET, POST`
- Sources: `observed_platform, platform_frontend`
- Description: Super selection simulation. / Discovered from platform frontend bundle.
- Request body: POST creates simulation.
- Tests:
- `GET` -> `200 OK`, `application/json`
- `POST` -> `skipped_mutating`; POST may mutate remote state; not executed by inventory test.

Response shape:

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
      
...
```

#### `/simulations/{simulation_id}`

- URL: `https://api.worldquantbrain.com/simulations/{simulation_id}`
- Methods: `GET`
- Sources: `observed_platform`
- Description: Simulation status/details.
- Official notes: `获取 simulation 当前状态。`
- Tests:
- `GET` -> `200 OK`, `application/json`

Response shape:

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

### `/suggest`

#### `/suggest/examples`

- URL: `https://api.worldquantbrain.com/suggest/examples`
- Methods: `GET, POST`
- Sources: `platform_frontend`
- Description: Suggestion examples. / Discovered from platform frontend bundle.
- Tests:
- `GET` -> `200 OK`, `application/json`
- `POST` -> `skipped_mutating`; POST may mutate remote state; not executed by inventory test.

Response shape:

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

#### `/suggest/expression`

- URL: `https://api.worldquantbrain.com/suggest/expression`
- Methods: `GET, POST`
- Sources: `platform_frontend`
- Description: Expression suggestion. / Discovered from platform frontend bundle.
- Request body: POST may send prompt/context.
- Tests:
- `GET` -> `404 Not Found`, `application/json`
- `POST` -> `skipped_mutating`; POST may mutate remote state; not executed by inventory test.

Response shape:

```json
{
  "detail": "str"
}
```

#### `/suggest/fastexpr`

- URL: `https://api.worldquantbrain.com/suggest/fastexpr`
- Methods: `GET, POST`
- Sources: `platform_frontend`
- Description: FastExpr suggestion. / Discovered from platform frontend bundle.
- Request body: POST may send prompt/context.
- Tests:
- `GET` -> `404 Not Found`, `application/json`
- `POST` -> `skipped_mutating`; POST may mutate remote state; not executed by inventory test.

Response shape:

```json
{
  "detail": "str"
}
```

#### `/suggest/fields`

- URL: `https://api.worldquantbrain.com/suggest/fields`
- Methods: `GET, POST`
- Sources: `platform_dynamic_capture, platform_frontend`
- Description: Field suggestion. / Discovered from platform frontend bundle.
- Request body: POST may send prompt/context.
- Tests:
- `GET` -> `200 OK`, `application/json`
- `POST` -> `skipped_mutating`; POST may mutate remote state; not executed by inventory test.

Response shape:

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

### `/tags`

#### `/tags`

- URL: `https://api.worldquantbrain.com/tags`
- Methods: `GET`
- Sources: `platform_frontend`
- Description: Tag list/search. / Discovered from platform frontend bundle.
- Tests:
- `GET` -> `200 OK`, `application/json`

Response shape:

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

### `/teams`

#### `/teams`

- URL: `https://api.worldquantbrain.com/teams`
- Methods: `GET`
- Sources: `platform_frontend`
- Description: Teams. / Discovered from platform frontend bundle.
- Tests:
- `GET` -> `405 Method Not Allowed`, `application/json`

Response shape:

```json
{
  "detail": "str"
}
```

### `/tutorial`

#### `/tutorial/{tutorial_slug}`

- URL: `https://api.worldquantbrain.com/tutorial/{tutorial_slug}`
- Methods: `GET`
- Sources: `platform_dynamic_capture`
- Description: Observed by passive platform network capture.
- Tests:
- `GET` -> `200 OK`, `application/json`

Response shape:

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

### `/tutorial-pages`

#### `/tutorial-pages`

- URL: `https://api.worldquantbrain.com/tutorial-pages`
- Methods: `GET`
- Sources: `platform_frontend`
- Description: Tutorial pages. / Discovered from platform frontend bundle.
- Tests:
- `GET` -> `404 Not Found`, `application/json`

Response shape:

```json
{
  "message": "str"
}
```

#### `/tutorial-pages/{page_id}`

- URL: `https://api.worldquantbrain.com/tutorial-pages/{page_id}`
- Methods: `GET`
- Sources: `observed_platform`
- Description: Tutorial page details.
- Tests:
- `GET` -> `404 Not Found`, `application/json`

Response shape:

```json
{
  "message": "str"
}
```

### `/tutorials`

#### `/tutorials`

- URL: `https://api.worldquantbrain.com/tutorials`
- Methods: `GET`
- Sources: `observed_platform, platform_frontend`
- Description: Tutorial list. / Discovered from platform frontend bundle.
- Params: `{"limit": "optional", "query": "limit=50"}`
- Tests:
- `GET` -> `200 OK`, `application/json`

Response shape:

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

### `/user`

#### `/user/email/change`

- URL: `https://api.worldquantbrain.com/user/email/change`
- Methods: `GET, POST`
- Sources: `platform_frontend`
- Description: Change email. / Discovered from platform frontend bundle.
- Request body: Account mutation.
- Tests:
- `GET` -> `405 Method Not Allowed`, `application/json`
- `POST` -> `skipped_mutating`; POST may mutate remote state; not executed by inventory test.

Response shape:

```json
{
  "detail": "str"
}
```

#### `/user/email/reverify`

- URL: `https://api.worldquantbrain.com/user/email/reverify`
- Methods: `GET, POST`
- Sources: `platform_frontend`
- Description: Reverify email. / Discovered from platform frontend bundle.
- Request body: Account mutation.
- Tests:
- `GET` -> `405 Method Not Allowed`, `application/json`
- `POST` -> `skipped_mutating`; POST may mutate remote state; not executed by inventory test.

Response shape:

```json
{
  "detail": "str"
}
```

#### `/user/email/verify`

- URL: `https://api.worldquantbrain.com/user/email/verify`
- Methods: `GET, POST`
- Sources: `platform_frontend`
- Description: Verify email. / Discovered from platform frontend bundle.
- Request body: Account mutation.
- Tests:
- `GET` -> `405 Method Not Allowed`, `application/json`
- `POST` -> `skipped_mutating`; POST may mutate remote state; not executed by inventory test.

Response shape:

```json
{
  "detail": "str"
}
```

#### `/user/password/change`

- URL: `https://api.worldquantbrain.com/user/password/change`
- Methods: `GET, POST`
- Sources: `platform_frontend`
- Description: Change password. / Discovered from platform frontend bundle.
- Request body: Account mutation.
- Tests:
- `GET` -> `405 Method Not Allowed`, `application/json`
- `POST` -> `skipped_mutating`; POST may mutate remote state; not executed by inventory test.

Response shape:

```json
{
  "detail": "str"
}
```

#### `/user/password/forgot`

- URL: `https://api.worldquantbrain.com/user/password/forgot`
- Methods: `GET, POST`
- Sources: `platform_frontend`
- Description: Forgot password. / Discovered from platform frontend bundle.
- Request body: Account mutation.
- Tests:
- `GET` -> `405 Method Not Allowed`, `application/json`
- `POST` -> `skipped_mutating`; POST may mutate remote state; not executed by inventory test.

Response shape:

```json
{
  "detail": "str"
}
```

#### `/user/password/reset`

- URL: `https://api.worldquantbrain.com/user/password/reset`
- Methods: `GET, POST`
- Sources: `platform_frontend`
- Description: Reset password. / Discovered from platform frontend bundle.
- Request body: Account mutation.
- Tests:
- `GET` -> `405 Method Not Allowed`, `application/json`
- `POST` -> `skipped_mutating`; POST may mutate remote state; not executed by inventory test.

Response shape:

```json
{
  "detail": "str"
}
```

#### `/user/token`

- URL: `https://api.worldquantbrain.com/user/token`
- Methods: `GET, POST`
- Sources: `platform_frontend`
- Description: User token endpoint. / Discovered from platform frontend bundle.
- Request body: Token operation.
- Tests:
- `GET` -> `405 Method Not Allowed`, `application/json`
- `POST` -> `skipped_mutating`; POST may mutate remote state; not executed by inventory test.

Response shape:

```json
{
  "detail": "str"
}
```

### `/users`

#### `/users`

- URL: `https://api.worldquantbrain.com/users`
- Methods: `GET`
- Sources: `platform_frontend`
- Description: Users collection. / Discovered from platform frontend bundle.
- Params: `{"limit": "optional"}`
- Tests:
- `GET` -> `405 Method Not Allowed`, `application/json`

Response shape:

```json
{
  "detail": "str"
}
```

#### `/users/self`

- URL: `https://api.worldquantbrain.com/users/self`
- Methods: `GET`
- Sources: `rocky-d/wqb`
- Description: Current user profile.
- Tests:
- `GET` -> `200 OK`, `application/json`

Response shape:

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

#### `/users/self/achievements`

- URL: `https://api.worldquantbrain.com/users/self/achievements`
- Methods: `GET`
- Sources: `platform_dynamic_capture`
- Description: Observed by passive platform network capture.
- Tests:
- `GET` -> `200 OK`, `application/json`

Response shape:

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

#### `/users/self/activities/pyramid-alphas`

- URL: `https://api.worldquantbrain.com/users/self/activities/pyramid-alphas`
- Methods: `GET`
- Sources: `observed_platform`
- Description: Current user's pyramid alpha counts.
- Params: `{"startDate": "YYYY-MM-DD", "endDate": "YYYY-MM-DD"}`
- Tests:
- `GET` -> `200 OK`, `application/json`

Response shape:

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

#### `/users/self/activities/pyramid-multipliers`

- URL: `https://api.worldquantbrain.com/users/self/activities/pyramid-multipliers`
- Methods: `GET`
- Sources: `observed_platform`
- Description: Current user's pyramid multipliers.
- Tests:
- `GET` -> `200 OK`, `application/json`

Response shape:

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

#### `/users/self/activities/simulations`

- URL: `https://api.worldquantbrain.com/users/self/activities/simulations`
- Methods: `GET`
- Sources: `platform_dynamic_capture`
- Description: Observed by passive platform network capture.
- Params: `{"date>": "observed query parameter"}`
- Tests:
- `GET` -> `200 OK`, `application/json`

Response shape:

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

#### `/users/self/agreements`

- URL: `https://api.worldquantbrain.com/users/self/agreements`
- Methods: `GET`
- Sources: `platform_dynamic_capture`
- Description: Observed by passive platform network capture.
- Tests:
- `GET` -> `200 OK`, `application/json`

Response shape:

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

#### `/users/self/alphas`

- URL: `https://api.worldquantbrain.com/users/self/alphas`
- Methods: `GET`
- Sources: `rocky-d/wqb`
- Description: Current user's alphas.
- Params: `{"limit": "1..100", "offset": "0..10000", "dateSubmitted": "range", "type": "REGULAR|SUPER", "color": "platform color", "tag": "tag filter"}`
- Tests:
- `GET` -> `200 OK`, `application/json`

Response shape:

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
  
...
```

#### `/users/self/alphas/summary`

- URL: `https://api.worldquantbrain.com/users/self/alphas/summary`
- Methods: `GET`
- Sources: `platform_dynamic_capture`
- Description: Observed by passive platform network capture.
- Tests:
- `GET` -> `200 OK`, `application/json`

Response shape:

```json
{
  "is": "int",
  "os": "int",
  "prod": "int"
}
```

#### `/users/self/consultant/summary`

- URL: `https://api.worldquantbrain.com/users/self/consultant/summary`
- Methods: `GET`
- Sources: `platform_dynamic_capture, platform_frontend`
- Description: Current consultant performance summary.
- Tests:
- `GET` -> `200 OK`, `application/json`

Response shape:

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
 
...
```

#### `/users/self/consultant/tutorial/summary`

- URL: `https://api.worldquantbrain.com/users/self/consultant/tutorial/summary`
- Methods: `GET, PATCH`
- Sources: `platform_dynamic_capture`
- Description: Observed by passive platform network capture.
- Request body: Observed request body shape in dynamic_capture.
- Tests:
- `GET` -> `200 OK`, `application/json`
- `PATCH` -> `skipped_mutating`; PATCH may mutate remote state; not executed by inventory test.

Response shape:

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

#### `/users/self/messages`

- URL: `https://api.worldquantbrain.com/users/self/messages`
- Methods: `GET`
- Sources: `observed_platform, platform_dynamic_capture`
- Description: Current user's messages.
- Params: `{"limit": "optional", "offset": "optional", "order": "observed query parameter", "type": "observed query parameter"}`
- Tests:
- `GET` -> `200 OK`, `application/json`

Response shape:

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

#### `/users/self/messages/summary`

- URL: `https://api.worldquantbrain.com/users/self/messages/summary`
- Methods: `GET`
- Sources: `platform_dynamic_capture`
- Description: Observed by passive platform network capture.
- Tests:
- `GET` -> `200 OK`, `application/json`

Response shape:

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

#### `/users/self/pyramid/alphas`

- URL: `https://api.worldquantbrain.com/users/self/pyramid/alphas`
- Methods: `GET`
- Sources: `observed_platform`
- Description: Fallback pyramid alpha endpoint.
- Params: `{"startDate": "YYYY-MM-DD", "endDate": "YYYY-MM-DD"}`
- Tests:
- `GET` -> `404 Not Found`, `application/json`

Response shape:

```json
{
  "detail": "str"
}
```

#### `/users/self/teams`

- URL: `https://api.worldquantbrain.com/users/self/teams`
- Methods: `GET`
- Sources: `platform_dynamic_capture`
- Description: Observed by passive platform network capture.
- Params: `{"members.self.status": "observed query parameter", "order": "observed query parameter", "status": "observed query parameter"}`
- Tests:
- `GET` -> `200 OK`, `application/json`

Response shape:

```json
{
  "count": "int",
  "next": "null",
  "previous": "null",
  "results": []
}
```

#### `/users/self/tutorial/steps`

- URL: `https://api.worldquantbrain.com/users/self/tutorial/steps`
- Methods: `GET`
- Sources: `platform_frontend`
- Description: Tutorial step state. / Discovered from platform frontend bundle.
- Tests:
- `GET` -> `200 OK`, `application/json`

Response shape:

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

#### `/users/self/tutorial/summary`

- URL: `https://api.worldquantbrain.com/users/self/tutorial/summary`
- Methods: `GET`
- Sources: `platform_frontend`
- Description: Tutorial summary state. / Discovered from platform frontend bundle.
- Tests:
- `GET` -> `200 OK`, `application/json`

Response shape:

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

#### `/users/{user_id}`

- URL: `https://api.worldquantbrain.com/users/{user_id}`
- Methods: `GET`
- Sources: `platform_dynamic_capture, rocky-d/wqb`
- Description: User profile by id.
- Tests:
- `GET` -> `200 OK`, `application/json`

Response shape:

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

#### `/users/{user_id}/achievements`

- URL: `https://api.worldquantbrain.com/users/{user_id}/achievements`
- Methods: `GET`
- Sources: `platform_dynamic_capture`
- Description: Observed by passive platform network capture.
- Tests:
- `GET` -> `200 OK`, `application/json`

Response shape:

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

#### `/users/{user_id}/activities`

- URL: `https://api.worldquantbrain.com/users/{user_id}/activities`
- Methods: `GET`
- Sources: `observed_platform`
- Description: User activities by id.
- Tests:
- `GET` -> `200 OK`, `application/json`

Response shape:

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

#### `/users/{user_id}/activities/diversity`

- URL: `https://api.worldquantbrain.com/users/{user_id}/activities/diversity`
- Methods: `GET`
- Sources: `official_doc_snippet`
- Description: 按 Region、Delay、Data Category 返回 alpha 提交分布。
- Official notes: `按 Region、Delay、Data Category 返回 alpha 提交分布。`
- Tests:
- `GET` -> `200 OK`, `application/json`

Response shape:

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

#### `/users/{user_id}/alphas`

- URL: `https://api.worldquantbrain.com/users/{user_id}/alphas`
- Methods: `OPTIONS`
- Sources: `platform_dynamic_capture`
- Description: Observed by passive platform network capture.
- Tests:
- `OPTIONS` -> `200 OK`, `application/json`

Response shape:

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
        "la
...
```

#### `/users/{user_id}/competitions`

- URL: `https://api.worldquantbrain.com/users/{user_id}/competitions`
- Methods: `GET`
- Sources: `observed_platform, platform_dynamic_capture`
- Description: User competitions by id.
- Tests:
- `GET` -> `200 OK`, `application/json`

Response shape:

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

#### `/users/{user_id}/settings/simulation`

- URL: `https://api.worldquantbrain.com/users/{user_id}/settings/simulation`
- Methods: `GET`
- Sources: `platform_dynamic_capture`
- Description: Observed by passive platform network capture.
- Tests:
- `GET` -> `200 OK`, `application/json`

Response shape:

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

### `/video-courses`

#### `/video-courses`

- URL: `https://api.worldquantbrain.com/video-courses`
- Methods: `GET`
- Sources: `platform_frontend`
- Description: Video courses. / Discovered from platform frontend bundle.
- Tests:
- `GET` -> `200 OK`, `application/json`

Response shape:

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

## Community SQLite

- Database: `None`
- Table count: `None`
- 远端 API 不直接提供论坛全文检索；社区内容按本地 SQLite schema 作为独立数据源记录。
