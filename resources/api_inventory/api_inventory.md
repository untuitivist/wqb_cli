# WorldQuant BRAIN API Inventory

- Base URL: `https://api.worldquantbrain.com`
- Generated at: `2026-07-16T08:57:52+00:00`
- Endpoint count: `107`
- Probed GET count: `61`
- Usable GET count: `31`
- 自动探测只执行 `GET`，不会自动执行 `POST/PATCH/PUT/DELETE`。
- 社区内容不在远端 API 中爬取，后续继续使用本地 SQLite 搜索。

## Sample IDs

- `alpha_id`: `vR5p8vqb`
- `dataset_id`: `analyst10`
- `competition_id`: `challenge`
- `event_id`: `zO8y3jm`
- `user_id`: `JL40454`

## Endpoints

### `/achievements`

- Methods: `GET`
- Sources: `platform_frontend`
- Description: Achievements. / Discovered from platform frontend bundle.
- Safe probe: `True`
- Probe URL: `https://api.worldquantbrain.com/achievements`
- OPTIONS: `{"status_code": 405, "allow": "GET, HEAD, OPTIONS", "content_type": "application/json"}`
- Allowed methods: `GET, HEAD, OPTIONS`
- Probe status: `200 OK`
- Usable GET: `True`
- Response shape: `[{"id": "str", "name": "str", "description": "str", "total": "int"}]`

### `/achievements/{achievement_id}/icon`

- Methods: `GET`
- Sources: `platform_dynamic_capture`
- Description: Observed by passive platform network capture.
- Safe probe: `True`
- Probe skipped/error: `Observed by platform dynamic network capture; no separate safe probe was run.`

### `/agreements`

- Methods: `GET`
- Sources: `platform_frontend`
- Description: Agreements. / Discovered from platform frontend bundle.
- Safe probe: `True`
- Probe URL: `https://api.worldquantbrain.com/agreements`
- OPTIONS: `{"status_code": 200, "allow": "GET, POST, HEAD, OPTIONS", "content_type": "application/json"}`
- Allowed methods: `GET, POST, HEAD, OPTIONS`
- Probe status: `405 Method Not Allowed`
- Usable GET: `False`
- Response shape: `{"detail": "str"}`

### `/alphas`

- Methods: `GET`
- Sources: `platform_frontend, rocky-d/wqb`
- Description: Alpha collection. / Discovered from platform frontend bundle.
- Safe probe: `True`
- Params: `{"limit": "1..100", "offset": "0..10000", "query": "limit=5"}`
- Probe URL: `https://api.worldquantbrain.com/alphas?limit=1`
- OPTIONS: `{"status_code": 200, "allow": "POST, PUT, PATCH, OPTIONS", "content_type": "application/json"}`
- Allowed methods: `POST, PUT, PATCH, OPTIONS`
- Probe status: `405 Method Not Allowed`
- Usable GET: `False`
- Response shape: `{"detail": "str"}`

### `/alphas/distribution`

- Methods: `GET`
- Sources: `platform_frontend`
- Description: Alpha distribution aggregate. / Discovered from platform frontend bundle.
- Safe probe: `True`
- Probe URL: `https://api.worldquantbrain.com/alphas/distribution`
- OPTIONS: `{"status_code": 200, "allow": "GET, PUT, PATCH, HEAD, OPTIONS", "content_type": "application/json"}`
- Allowed methods: `GET, PUT, PATCH, HEAD, OPTIONS`
- Probe status: `404 Not Found`
- Usable GET: `False`
- Response shape: `{"detail": "str"}`

### `/alphas/lists`

- Methods: `GET`
- Sources: `platform_frontend`
- Description: Alpha lists. / Discovered from platform frontend bundle.
- Safe probe: `True`
- Probe URL: `https://api.worldquantbrain.com/alphas/lists`
- OPTIONS: `{"status_code": 200, "allow": "GET, PUT, PATCH, HEAD, OPTIONS", "content_type": "application/json"}`
- Allowed methods: `GET, PUT, PATCH, HEAD, OPTIONS`
- Probe status: `404 Not Found`
- Usable GET: `False`
- Response shape: `{"detail": "str"}`

### `/alphas/sample-alpha-id-walkthrough`

- Methods: `GET`
- Sources: `platform_frontend`
- Description: Discovered from platform frontend bundle.
- Safe probe: `True`
- Probe URL: `https://api.worldquantbrain.com/alphas/sample-alpha-id-walkthrough`
- OPTIONS: `{"status_code": 200, "allow": "GET, PUT, PATCH, HEAD, OPTIONS", "content_type": "application/json"}`
- Allowed methods: `GET, PUT, PATCH, HEAD, OPTIONS`
- Probe status: `404 Not Found`
- Usable GET: `False`
- Response shape: `{"detail": "str"}`

### `/alphas/super-selection`

- Methods: `GET`
- Sources: `platform_frontend`
- Description: Super selection alpha endpoint. / Discovered from platform frontend bundle.
- Safe probe: `True`
- Probe URL: `https://api.worldquantbrain.com/alphas/super-selection`
- OPTIONS: `{"status_code": 200, "allow": "GET, PUT, PATCH, HEAD, OPTIONS", "content_type": "application/json"}`
- Allowed methods: `GET, PUT, PATCH, HEAD, OPTIONS`
- Probe status: `404 Not Found`
- Usable GET: `False`
- Response shape: `{"detail": "str"}`

### `/alphas/unsubmitted`

- Methods: `GET`
- Sources: `platform_frontend`
- Description: Unsubmitted alpha endpoint. / Discovered from platform frontend bundle.
- Safe probe: `True`
- Probe URL: `https://api.worldquantbrain.com/alphas/unsubmitted`
- OPTIONS: `{"status_code": 200, "allow": "GET, PUT, PATCH, HEAD, OPTIONS", "content_type": "application/json"}`
- Allowed methods: `GET, PUT, PATCH, HEAD, OPTIONS`
- Probe status: `404 Not Found`
- Usable GET: `False`
- Response shape: `{"detail": "str"}`

### `/alphas/{alpha_id}`

- Methods: `GET, PATCH`
- Sources: `platform_frontend, rocky-d/wqb`
- Description: Alpha details or property patch. / Discovered from platform frontend bundle.
- Safe probe: `False`
- Request body: PATCH updates alpha properties.
- Probe: skipped

### `/alphas/{alpha_id}/alphas`

- Methods: `GET`
- Sources: `platform_frontend`
- Description: Discovered from platform frontend bundle.
- Safe probe: `True`
- Probe URL: `https://api.worldquantbrain.com/alphas/vR5p8vqb/alphas`
- OPTIONS: `{"status_code": 200, "allow": "GET, HEAD, OPTIONS", "content_type": "application/json"}`
- Allowed methods: `GET, HEAD, OPTIONS`
- Probe status: `404 Not Found`
- Usable GET: `False`
- Response shape: `{"detail": "str"}`

### `/alphas/{alpha_id}/check`

- Methods: `GET`
- Sources: `rocky-d/wqb`
- Description: Alpha simulation check.
- Safe probe: `False`
- Probe: skipped

### `/alphas/{alpha_id}/correlations`

- Methods: `GET`
- Sources: `observed_platform`
- Description: Alpha correlation base endpoint.
- Safe probe: `False`
- Probe: skipped

### `/alphas/{alpha_id}/correlations/power-pool`

- Methods: `GET`
- Sources: `observed_platform`
- Description: Power Pool correlation.
- Safe probe: `False`
- Probe: skipped

### `/alphas/{alpha_id}/correlations/prod`

- Methods: `GET`
- Sources: `observed_platform`
- Description: Production correlation.
- Safe probe: `False`
- Probe: skipped

### `/alphas/{alpha_id}/correlations/self`

- Methods: `GET`
- Sources: `observed_platform`
- Description: Self correlation.
- Safe probe: `False`
- Probe: skipped

### `/alphas/{alpha_id}/performance-comparison`

- Methods: `GET`
- Sources: `observed_platform`
- Description: Before/after performance comparison.
- Safe probe: `False`
- Probe: skipped

### `/alphas/{alpha_id}/recordsets`

- Methods: `GET`
- Sources: `observed_platform`
- Description: Alpha recordset index.
- Safe probe: `False`
- Probe: skipped

### `/alphas/{alpha_id}/recordsets/pnl`

- Methods: `GET`
- Sources: `observed_platform`
- Description: PNL recordset.
- Safe probe: `False`
- Probe: skipped

### `/alphas/{alpha_id}/recordsets/sharpe`

- Methods: `GET`
- Sources: `observed_platform`
- Description: Sharpe recordset.
- Safe probe: `False`
- Probe: skipped

### `/alphas/{alpha_id}/recordsets/yearly-stats`

- Methods: `GET`
- Sources: `observed_platform`
- Description: Yearly stats recordset.
- Safe probe: `False`
- Probe: skipped

### `/alphas/{alpha_id}/submit`

- Methods: `POST`
- Sources: `rocky-d/wqb`
- Description: Submit alpha.
- Safe probe: `False`
- Request body: Submission action. Has side effect.
- Probe: skipped

### `/authentication`

- Methods: `DELETE, GET, HEAD, POST`
- Sources: `platform_dynamic_capture, platform_frontend, rocky-d/wqb`
- Description: Authentication session endpoint. / Discovered from platform frontend bundle.
- Safe probe: `True`
- Probe URL: `https://api.worldquantbrain.com/authentication`
- OPTIONS: `{"status_code": 200, "allow": "GET, POST, DELETE, HEAD, OPTIONS", "content_type": "application/json"}`
- Allowed methods: `GET, POST, DELETE, HEAD, OPTIONS`
- Probe status: `200 OK`
- Usable GET: `True`
- Response shape: `{"user": {"id": "str"}, "token": {"expiry": "float"}, "permissions": ["str"]}`

### `/authentication/brainlabs`

- Methods: `GET`
- Sources: `platform_frontend`
- Description: Discovered from platform frontend bundle.
- Safe probe: `True`
- Probe URL: `https://api.worldquantbrain.com/authentication/brainlabs`
- OPTIONS: `{"status_code": 200, "allow": "GET, POST, HEAD, OPTIONS", "content_type": "application/json"}`
- Allowed methods: `GET, POST, HEAD, OPTIONS`
- Probe status: `200 OK`
- Usable GET: `True`
- Response shape: `"text"`

### `/authentication/persona`

- Methods: `GET`
- Sources: `platform_frontend`
- Description: Discovered from platform frontend bundle.
- Safe probe: `True`
- Probe URL: `https://api.worldquantbrain.com/authentication/persona`
- OPTIONS: `{"status_code": 200, "allow": "GET, POST, HEAD, OPTIONS", "content_type": "application/json"}`
- Allowed methods: `GET, POST, HEAD, OPTIONS`
- Probe status: `400 Bad Request`
- Usable GET: `False`
- Response shape: `["str"]`

### `/authentication/support`

- Methods: `GET`
- Sources: `platform_frontend`
- Description: Discovered from platform frontend bundle.
- Safe probe: `True`
- Params: `{"query": "return_to="}`
- Probe URL: `https://api.worldquantbrain.com/authentication/support`
- OPTIONS: `{"status_code": 200, "allow": "GET, HEAD, OPTIONS", "content_type": "application/json"}`
- Allowed methods: `GET, HEAD, OPTIONS`
- Probe status: `403 Forbidden`
- Usable GET: `False`
- Response shape: `"text"`

### `/authentication/workday`

- Methods: `GET`
- Sources: `platform_frontend`
- Description: Discovered from platform frontend bundle.
- Safe probe: `True`
- Probe URL: `https://api.worldquantbrain.com/authentication/workday`
- OPTIONS: `{"status_code": 200, "allow": "GET, POST, HEAD, OPTIONS", "content_type": "application/json"}`
- Allowed methods: `GET, POST, HEAD, OPTIONS`
- Probe status: `200 OK`
- Usable GET: `True`
- Response shape: `"text"`

### `/captcha`

- Methods: `GET`
- Sources: `platform_dynamic_capture`
- Description: Observed by passive platform network capture.
- Safe probe: `True`
- Probe skipped/error: `Observed by platform dynamic network capture; no separate safe probe was run.`

### `/competition-levels`

- Methods: `GET`
- Sources: `platform_dynamic_capture, platform_frontend`
- Description: Competition levels. / Discovered from platform frontend bundle.
- Safe probe: `True`
- Probe URL: `https://api.worldquantbrain.com/competition-levels`
- OPTIONS: `{"status_code": 405, "allow": "GET, HEAD, OPTIONS", "content_type": "application/json"}`
- Allowed methods: `GET, HEAD, OPTIONS`
- Probe status: `200 OK`
- Usable GET: `True`
- Response shape: `[{"id": "str", "name": "str"}]`

### `/competition-levels/{competition_level_id}/icon`

- Methods: `GET`
- Sources: `platform_dynamic_capture`
- Description: Observed by passive platform network capture.
- Safe probe: `True`
- Probe skipped/error: `Observed by platform dynamic network capture; no separate safe probe was run.`

### `/competitions`

- Methods: `GET`
- Sources: `observed_platform, platform_dynamic_capture, platform_frontend`
- Description: Competitions list. / Discovered from platform frontend bundle.
- Safe probe: `True`
- Params: `{"limit": "optional", "offset": "optional"}`
- Probe URL: `https://api.worldquantbrain.com/competitions?limit=1`
- OPTIONS: `{"status_code": 200, "allow": "GET, HEAD, OPTIONS", "content_type": "application/json"}`
- Allowed methods: `GET, HEAD, OPTIONS`
- Probe status: `200 OK`
- Usable GET: `True`
- Response shape: `{"count": "int", "next": "str", "previous": "NoneType", "results": [{"id": "str", "name": "str", "description": "str", "universities": "NoneType", "countries": "NoneType", "excludedCountries": "NoneType", "status": "str", "teamBased": "bool", "startDate": "NoneType", "endDate": "NoneType", "signUpStartDate": "NoneType", "signUpEndDate": "NoneType", "signUpDate": "NoneType", "team": "NoneType", "scoring": "str", "leaderboard": "NoneType", "prizeBoard": "bool", "universityBoard": "bool", "submissions": "bool", "faq": "str", "progress": "NoneType"}]}`

### `/competitions/{competition_id}`

- Methods: `GET`
- Sources: `observed_platform`
- Description: Competition details.
- Safe probe: `False`
- Probe: skipped

### `/competitions/{competition_id}/boards/{board_type}`

- Methods: `GET`
- Sources: `observed_platform, platform_frontend`
- Description: Generic competition leaderboard; use `OPTIONS` to discover board-specific fields, filters, and aggregations.
- Probe: `200 OK` using `PAC2026/boards/leader`

### `/competitions/spc/submissions`

- Methods: `GET, POST`
- Sources: `observed_platform, platform_frontend`
- Description: List or create SPC prompt submissions.
- Probe: `200 OK`; mutating `POST` was not executed.

### `/competitions/spc/submissions/{submission_id}`

- Methods: `GET, PUT, PATCH`
- Sources: `observed_platform, platform_frontend`
- Description: Read submission weight history or replace/partially update an SPC prompt submission.
- Probe: `200 OK`; mutating `PUT/PATCH` were not executed.

### `/competitions/{competition_id}/agreement`

- Methods: `GET, POST`
- Sources: `observed_platform`
- Description: Competition agreement.
- Safe probe: `False`
- Request body: POST may accept agreement.
- Probe: skipped

### `/configuration`

- Methods: `GET`
- Sources: `platform_dynamic_capture, platform_frontend`
- Description: Platform configuration. / Discovered from platform frontend bundle.
- Safe probe: `True`
- Probe URL: `https://api.worldquantbrain.com/configuration`
- OPTIONS: `{"status_code": 200, "allow": "GET, HEAD, OPTIONS", "content_type": "application/json"}`
- Allowed methods: `GET, HEAD, OPTIONS`
- Probe status: `200 OK`
- Usable GET: `True`
- Response shape: `{"analytics": {"trackingId": "NoneType"}, "recaptcha": {"siteKey": "str"}, "recaptchaV3": {"siteKey": "str"}}`

### `/consultant`

- Methods: `GET`
- Sources: `platform_frontend`
- Description: Consultant landing endpoint. / Discovered from platform frontend bundle.
- Safe probe: `True`
- Probe URL: `https://api.worldquantbrain.com/consultant`
- OPTIONS: `{"status_code": 404, "allow": null, "content_type": "application/json"}`
- Probe status: `404 Not Found`
- Usable GET: `False`
- Response shape: `{"detail": "str"}`

### `/consultant-datasets`

- Methods: `GET`
- Sources: `platform_frontend`
- Description: Consultant datasets. / Discovered from platform frontend bundle.
- Safe probe: `True`
- Probe URL: `https://api.worldquantbrain.com/consultant-datasets`
- OPTIONS: `{"status_code": 404, "allow": null, "content_type": "application/json"}`
- Probe status: `404 Not Found`
- Usable GET: `False`
- Response shape: `{"detail": "str"}`

### `/consultant-information/consultant-dos-and-donts`

- Methods: `GET`
- Sources: `platform_frontend`
- Description: Consultant information article. / Discovered from platform frontend bundle.
- Safe probe: `True`
- Probe URL: `https://api.worldquantbrain.com/consultant-information/consultant-dos-and-donts`
- OPTIONS: `{"status_code": 404, "allow": null, "content_type": "application/json"}`
- Probe status: `404 Not Found`
- Usable GET: `False`
- Response shape: `{"detail": "str"}`

### `/consultant-information/consultant-faqs`

- Methods: `GET`
- Sources: `platform_frontend`
- Description: Consultant FAQ article. / Discovered from platform frontend bundle.
- Safe probe: `True`
- Probe URL: `https://api.worldquantbrain.com/consultant-information/consultant-faqs`
- OPTIONS: `{"status_code": 404, "allow": null, "content_type": "application/json"}`
- Probe status: `404 Not Found`
- Usable GET: `False`
- Response shape: `{"detail": "str"}`

### `/consultant-information/osmosis-allocation-guide-consultants`

- Methods: `GET`
- Sources: `platform_frontend`
- Description: Osmosis allocation guide. / Discovered from platform frontend bundle.
- Safe probe: `True`
- Probe URL: `https://api.worldquantbrain.com/consultant-information/osmosis-allocation-guide-consultants`
- OPTIONS: `{"status_code": 404, "allow": null, "content_type": "application/json"}`
- Probe status: `404 Not Found`
- Usable GET: `False`
- Response shape: `{"detail": "str"}`

### `/consultant-information/visualization-tool`

- Methods: `GET`
- Sources: `platform_frontend`
- Description: Visualization tool guide. / Discovered from platform frontend bundle.
- Safe probe: `True`
- Probe URL: `https://api.worldquantbrain.com/consultant-information/visualization-tool`
- OPTIONS: `{"status_code": 404, "allow": null, "content_type": "application/json"}`
- Probe status: `404 Not Found`
- Usable GET: `False`
- Response shape: `{"detail": "str"}`

### `/consultant-program`

- Methods: `GET`
- Sources: `platform_frontend`
- Description: Discovered from platform frontend bundle.
- Safe probe: `True`
- Probe URL: `https://api.worldquantbrain.com/consultant-program`
- OPTIONS: `{"status_code": 404, "allow": null, "content_type": "application/json"}`
- Probe status: `404 Not Found`
- Usable GET: `False`
- Response shape: `{"detail": "str"}`

### `/consultant-program/{language}`

- Methods: `GET`
- Sources: `platform_frontend`
- Description: Consultant program by language. / Discovered from platform frontend bundle.
- Safe probe: `False`
- Probe: skipped

### `/consultant/boards`

- Methods: `GET`
- Sources: `platform_frontend`
- Description: Consultant boards. / Discovered from platform frontend bundle.
- Safe probe: `True`
- Probe URL: `https://api.worldquantbrain.com/consultant/boards`
- OPTIONS: `{"status_code": 404, "allow": null, "content_type": "application/json"}`
- Probe status: `404 Not Found`
- Usable GET: `False`
- Response shape: `{"detail": "str"}`

### `/consultant/boards/leader`

- Methods: `GET`
- Sources: `observed_platform, platform_dynamic_capture`
- Description: Consultant leaderboard.
- Safe probe: `True`
- Params: `{"user": "observed query parameter"}`
- Probe URL: `https://api.worldquantbrain.com/consultant/boards/leader`
- OPTIONS: `{"status_code": 200, "allow": "GET, HEAD, OPTIONS", "content_type": "application/json"}`
- Allowed methods: `GET, HEAD, OPTIONS`
- Probe status: `200 OK`
- Usable GET: `True`
- Response shape: `{"count": "int", "next": "str", "previous": "NoneType", "results": [{"user": "str", "weightFactor": "float", "valueFactor": "float", "dailyOsmosisRank": "float", "dataFieldsUsed": "int", "submissionsCount": "int", "meanProdCorrelation": "float", "meanSelfCorrelation": "float", "superAlphaSubmissionsCount": "int", "superAlphaMeanProdCorrelation": "float", "superAlphaMeanSelfCorrelation": "float", "university": "str", "country": "str"}]}`

### `/consultant/boards/{board_type}`

- Methods: `GET`
- Sources: `observed_platform, platform_frontend`
- Description: Generic consultant leaderboard for board types such as `leader`, `spc`, `power-pool`, and `referral`.
- Probe: `200 OK` for live `GET` and `OPTIONS` checks.

### `/consultant/boards/spc`

- Methods: `GET`
- Sources: `observed_platform, platform_frontend`
- Description: Static SPC instance retained alongside the generic consultant-board template.
- Probe: `200 OK`

### `/consultant/summary`

- Methods: `GET`
- Sources: `platform_frontend`
- Description: Consultant summary endpoint observed in frontend. / Discovered from platform frontend bundle.
- Safe probe: `True`
- Probe URL: `https://api.worldquantbrain.com/consultant/summary`
- OPTIONS: `{"status_code": 404, "allow": null, "content_type": "application/json"}`
- Probe status: `404 Not Found`
- Usable GET: `False`
- Response shape: `{"detail": "str"}`

### `/data-categories`

- Methods: `GET`
- Sources: `platform_dynamic_capture, platform_frontend, rocky-d/wqb`
- Description: Data categories. / Discovered from platform frontend bundle.
- Safe probe: `True`
- Probe URL: `https://api.worldquantbrain.com/data-categories`
- OPTIONS: `{"status_code": 200, "allow": "GET, HEAD, OPTIONS", "content_type": "application/json"}`
- Allowed methods: `GET, HEAD, OPTIONS`
- Probe status: `200 OK`
- Usable GET: `True`
- Response shape: `[{"id": "str", "name": "str", "datasetCount": "int", "fieldCount": "int", "alphaCount": "int", "userCount": "int", "valueScore": "float", "region": ["str"], "children": [{"id": "...", "name": "...", "datasetCount": "...", "fieldCount": "...", "alphaCount": "...", "userCount": "...", "valueScore": "...", "region": "..."}]}]`

### `/data-fields`

- Methods: `GET`
- Sources: `platform_dynamic_capture, platform_frontend, rocky-d/wqb`
- Description: Data field search. / Discovered from platform frontend bundle.
- Safe probe: `True`
- Params: `{"dataset.id": "dataset id", "search": "query", "limit": "1..100", "offset": "0..10000", "delay": "observed query parameter", "instrumentType": "observed query parameter", "region": "observed query parameter", "universe": "observed query parameter"}`
- Probe URL: `https://api.worldquantbrain.com/data-fields?instrumentType=EQUITY&region=USA&delay=1&universe=TOP3000&limit=1`
- OPTIONS: `{"status_code": 200, "allow": "GET, HEAD, OPTIONS", "content_type": "application/json"}`
- Allowed methods: `GET, HEAD, OPTIONS`
- Probe status: `200 OK`
- Usable GET: `True`
- Response shape: `{"count": "int", "results": [{"id": "str", "description": "str", "dataset": {"id": "...", "name": "..."}, "category": {"id": "...", "name": "..."}, "subcategory": {"id": "...", "name": "..."}, "region": "str", "delay": "int", "universe": "str", "type": "str", "dateCoverage": "float", "coverage": "float", "userCount": "int", "alphaCount": "int", "pyramidMultiplier": "float", "themes": []}]}`

### `/data-fields/summary`

- Methods: `GET`
- Sources: `platform_frontend`
- Description: Data field summary aggregate. / Discovered from platform frontend bundle.
- Safe probe: `True`
- Probe URL: `https://api.worldquantbrain.com/data-fields/summary`
- OPTIONS: `{"status_code": 500, "allow": "GET, HEAD, OPTIONS", "content_type": "application/json"}`
- Allowed methods: `GET, HEAD, OPTIONS`
- Probe status: `429 Too Many Requests`
- Usable GET: `False`
- Response shape: `{"message": "str"}`

### `/data-fields/{field_id}`

- Methods: `GET`
- Sources: `rocky-d/wqb`
- Description: Data field details.
- Safe probe: `False`
- Probe: skipped

### `/data-sets`

- Methods: `GET`
- Sources: `platform_dynamic_capture, platform_frontend, rocky-d/wqb`
- Description: Data set search. / Discovered from platform frontend bundle.
- Safe probe: `True`
- Params: `{"instrumentType": "EQUITY", "region": "region", "delay": "delay", "universe": "universe", "limit": "1..100", "offset": "0..10000", "theme": "observed query parameter"}`
- Probe URL: `https://api.worldquantbrain.com/data-sets?instrumentType=EQUITY&region=USA&delay=1&universe=TOP3000&limit=1`
- OPTIONS: `{"status_code": 200, "allow": "GET, HEAD, OPTIONS", "content_type": "application/json"}`
- Allowed methods: `GET, HEAD, OPTIONS`
- Probe status: `200 OK`
- Usable GET: `True`
- Response shape: `{"count": "int", "results": [{"id": "str", "name": "str", "description": "str", "category": {"id": "...", "name": "..."}, "subcategory": {"id": "...", "name": "..."}, "region": "str", "delay": "int", "universe": "str", "dateCoverage": "float", "coverage": "float", "valueScore": "float", "userCount": "int", "alphaCount": "int", "fieldCount": "int", "pyramidMultiplier": "float", "themes": [], "researchPapers": ["..."]}]}`

### `/data-sets/search`

- Methods: `GET, POST`
- Sources: `platform_frontend`
- Description: Dataset search helper. / Discovered from platform frontend bundle.
- Safe probe: `True`
- Probe URL: `https://api.worldquantbrain.com/data-sets/search`
- OPTIONS: `{"status_code": 500, "allow": "GET, HEAD, OPTIONS", "content_type": "application/json"}`
- Allowed methods: `GET, HEAD, OPTIONS`
- Probe status: `400 Bad Request`
- Usable GET: `False`
- Response shape: `{"detail": "str"}`

### `/data-sets/{dataset_id}`

- Methods: `GET`
- Sources: `rocky-d/wqb`
- Description: Dataset details.
- Safe probe: `False`
- Probe: skipped

### `/errors/api/2/envelope`

- Methods: `POST`
- Sources: `platform_dynamic_capture`
- Description: Observed by passive platform network capture.
- Safe probe: `False`
- Params: `{"sentry_client": "observed query parameter", "sentry_key": "observed query parameter", "sentry_version": "observed query parameter"}`
- Request body: Observed request body shape in dynamic_capture.
- Probe skipped/error: `Observed by platform dynamic network capture; no separate safe probe was run.`

### `/events`

- Methods: `GET, OPTIONS`
- Sources: `observed_platform, platform_dynamic_capture, platform_frontend`
- Description: Events list. / Discovered from platform frontend bundle.
- Safe probe: `True`
- Params: `{"limit": "optional", "offset": "optional", "order": "observed query parameter", "start>": "observed query parameter"}`
- Probe URL: `https://api.worldquantbrain.com/events?limit=1`
- OPTIONS: `{"status_code": 200, "allow": "GET, HEAD, OPTIONS", "content_type": "application/json"}`
- Allowed methods: `GET, HEAD, OPTIONS`
- Probe status: `200 OK`
- Usable GET: `True`
- Response shape: `{"count": "int", "next": "str", "previous": "NoneType", "results": [{"id": "str", "title": "str", "type": "str", "category": "NoneType", "start": "str", "end": "str", "timezone": "str", "language": "str", "description": "str", "register": "str", "venue": "NoneType", "city": "NoneType", "country": "str"}]}`

### `/events/{event_id}`

- Methods: `GET`
- Sources: `platform_frontend`
- Description: Event details. / Discovered from platform frontend bundle.
- Safe probe: `False`
- Probe: skipped

### `/messages`

- Methods: `GET`
- Sources: `platform_frontend`
- Description: Message collection. / Discovered from platform frontend bundle.
- Safe probe: `True`
- Probe URL: `https://api.worldquantbrain.com/messages`
- OPTIONS: `{"status_code": 404, "allow": null, "content_type": "application/json"}`
- Probe status: `404 Not Found`
- Usable GET: `False`
- Response shape: `{"detail": "str"}`

### `/operators`

- Methods: `GET`
- Sources: `platform_dynamic_capture, platform_frontend, rocky-d/wqb`
- Description: Operator list/search. / Discovered from platform frontend bundle.
- Safe probe: `True`
- Params: `{"instrumentType": "optional", "region": "optional", "delay": "optional"}`
- Probe URL: `https://api.worldquantbrain.com/operators`
- OPTIONS: `{"status_code": 200, "allow": "GET, HEAD, OPTIONS", "content_type": "application/json"}`
- Allowed methods: `GET, HEAD, OPTIONS`
- Probe status: `200 OK`
- Usable GET: `True`
- Response shape: `[{"name": "str", "category": "str", "scope": ["str"], "definition": "str", "description": "str", "documentation": "str", "level": "str"}]`

### `/search`

- Methods: `GET`
- Sources: `platform_frontend`
- Description: Global search. / Discovered from platform frontend bundle.
- Safe probe: `True`
- Params: `{"query": "search text"}`
- Probe URL: `https://api.worldquantbrain.com/search`
- OPTIONS: `{"status_code": 200, "allow": "GET, HEAD, OPTIONS", "content_type": "application/json"}`
- Allowed methods: `GET, HEAD, OPTIONS`
- Probe status: `400 Bad Request`
- Usable GET: `False`
- Response shape: `{"query": ["str"]}`

### `/simulations`

- Methods: `GET, OPTIONS, POST`
- Sources: `platform_dynamic_capture, platform_frontend, rocky-d/wqb`
- Description: Simulation collection and simulation creation. / Discovered from platform frontend bundle.
- Safe probe: `True`
- Request body: POST creates simulation. Do not auto-probe POST.
- Probe URL: `https://api.worldquantbrain.com/simulations`
- OPTIONS: `{"status_code": 200, "allow": "POST, OPTIONS", "content_type": "application/json"}`
- Allowed methods: `POST, OPTIONS`
- Probe status: `405 Method Not Allowed`
- Usable GET: `False`
- Response shape: `{"detail": "str"}`

### `/simulations/super-selection`

- Methods: `GET, POST`
- Sources: `observed_platform, platform_frontend`
- Description: Super selection simulation. / Discovered from platform frontend bundle.
- Safe probe: `False`
- Request body: POST creates simulation.
- Probe: skipped

### `/simulations/{simulation_id}`

- Methods: `GET`
- Sources: `observed_platform`
- Description: Simulation status/details.
- Safe probe: `False`
- Probe: skipped

### `/suggest/examples`

- Methods: `GET, POST`
- Sources: `platform_frontend`
- Description: Suggestion examples. / Discovered from platform frontend bundle.
- Safe probe: `True`
- Probe URL: `https://api.worldquantbrain.com/suggest/examples`
- OPTIONS: `{"status_code": 200, "allow": "GET, HEAD, OPTIONS", "content_type": "application/json"}`
- Allowed methods: `GET, HEAD, OPTIONS`
- Probe status: `200 OK`
- Usable GET: `True`
- Response shape: `{"count": "int", "next": "str", "previous": "NoneType", "results": [{"settings": {"instrumentType": "...", "region": "...", "universe": "...", "delay": "...", "decay": "...", "neutralization": "...", "truncation": "...", "pasteurization": "...", "unitHandling": "...", "nanHandling": "...", "language": "...", "testPeriod": "...", "maxTrade": "...", "maxPosition": "..."}, "type": "str", "regular": "str"}]}`

### `/suggest/expression`

- Methods: `GET, POST`
- Sources: `platform_frontend`
- Description: Expression suggestion. / Discovered from platform frontend bundle.
- Safe probe: `True`
- Request body: POST may send prompt/context.
- Probe URL: `https://api.worldquantbrain.com/suggest/expression`
- OPTIONS: `{"status_code": 404, "allow": null, "content_type": "application/json"}`
- Probe status: `404 Not Found`
- Usable GET: `False`
- Response shape: `{"detail": "str"}`

### `/suggest/fastexpr`

- Methods: `GET, POST`
- Sources: `platform_frontend`
- Description: FastExpr suggestion. / Discovered from platform frontend bundle.
- Safe probe: `True`
- Request body: POST may send prompt/context.
- Probe URL: `https://api.worldquantbrain.com/suggest/fastexpr`
- OPTIONS: `{"status_code": 404, "allow": null, "content_type": "application/json"}`
- Probe status: `404 Not Found`
- Usable GET: `False`
- Response shape: `{"detail": "str"}`

### `/suggest/fields`

- Methods: `GET, POST`
- Sources: `platform_dynamic_capture, platform_frontend`
- Description: Field suggestion. / Discovered from platform frontend bundle.
- Safe probe: `True`
- Request body: POST may send prompt/context.
- Probe URL: `https://api.worldquantbrain.com/suggest/fields`
- OPTIONS: `{"status_code": 200, "allow": "GET, HEAD, OPTIONS", "content_type": "application/json"}`
- Allowed methods: `GET, HEAD, OPTIONS`
- Probe status: `200 OK`
- Usable GET: `True`
- Response shape: `{"selection": ["str"], "combo": ["str"]}`

### `/tags`

- Methods: `GET`
- Sources: `platform_frontend`
- Description: Tag list/search. / Discovered from platform frontend bundle.
- Safe probe: `True`
- Probe URL: `https://api.worldquantbrain.com/tags`
- OPTIONS: `{"status_code": 200, "allow": "GET, POST, HEAD, OPTIONS", "content_type": "application/json"}`
- Allowed methods: `GET, POST, HEAD, OPTIONS`
- Probe status: `200 OK`
- Usable GET: `True`
- Response shape: `{"count": "int", "next": "str", "previous": "NoneType", "results": [{"id": "str", "type": "str", "name": "str", "alphas": ["..."]}]}`

### `/teams`

- Methods: `GET`
- Sources: `platform_frontend`
- Description: Teams. / Discovered from platform frontend bundle.
- Safe probe: `True`
- Probe URL: `https://api.worldquantbrain.com/teams`
- OPTIONS: `{"status_code": 200, "allow": "POST, OPTIONS", "content_type": "application/json"}`
- Allowed methods: `POST, OPTIONS`
- Probe status: `405 Method Not Allowed`
- Usable GET: `False`
- Response shape: `{"detail": "str"}`

### `/tutorial-pages`

- Methods: `GET`
- Sources: `platform_frontend`
- Description: Tutorial pages. / Discovered from platform frontend bundle.
- Safe probe: `True`
- Probe URL: `https://api.worldquantbrain.com/tutorial-pages`
- OPTIONS: `{"status_code": 200, "allow": "GET, HEAD, OPTIONS", "content_type": "application/json"}`
- Allowed methods: `GET, HEAD, OPTIONS`
- Probe status: `404 Not Found`
- Usable GET: `False`
- Response shape: `{"message": "str"}`

### `/tutorial-pages/{page_id}`

- Methods: `GET`
- Sources: `observed_platform`
- Description: Tutorial page details.
- Safe probe: `False`
- Probe: skipped

### `/tutorial/{tutorial_slug}`

- Methods: `GET`
- Sources: `platform_dynamic_capture`
- Description: Observed by passive platform network capture.
- Safe probe: `True`
- Probe skipped/error: `Observed by platform dynamic network capture; no separate safe probe was run.`

### `/tutorials`

- Methods: `GET`
- Sources: `observed_platform, platform_frontend`
- Description: Tutorial list. / Discovered from platform frontend bundle.
- Safe probe: `True`
- Params: `{"limit": "optional", "query": "limit=50"}`
- Probe URL: `https://api.worldquantbrain.com/tutorials?limit=1`
- OPTIONS: `{"status_code": 200, "allow": "GET, HEAD, OPTIONS", "content_type": "application/json"}`
- Allowed methods: `GET, HEAD, OPTIONS`
- Probe status: `200 OK`
- Usable GET: `True`
- Response shape: `{"count": "int", "next": "str", "previous": "NoneType", "results": [{"id": "str", "category": "str", "pages": ["..."], "title": "str", "sequence": "int", "lastModified": "str"}]}`

### `/user/email/change`

- Methods: `GET, POST`
- Sources: `platform_frontend`
- Description: Change email. / Discovered from platform frontend bundle.
- Safe probe: `False`
- Request body: Account mutation.
- Probe: skipped

### `/user/email/reverify`

- Methods: `GET, POST`
- Sources: `platform_frontend`
- Description: Reverify email. / Discovered from platform frontend bundle.
- Safe probe: `False`
- Request body: Account mutation.
- Probe: skipped

### `/user/email/verify`

- Methods: `GET, POST`
- Sources: `platform_frontend`
- Description: Verify email. / Discovered from platform frontend bundle.
- Safe probe: `False`
- Request body: Account mutation.
- Probe: skipped

### `/user/password/change`

- Methods: `GET, POST`
- Sources: `platform_frontend`
- Description: Change password. / Discovered from platform frontend bundle.
- Safe probe: `False`
- Request body: Account mutation.
- Probe: skipped

### `/user/password/forgot`

- Methods: `GET, POST`
- Sources: `platform_frontend`
- Description: Forgot password. / Discovered from platform frontend bundle.
- Safe probe: `False`
- Request body: Account mutation.
- Probe: skipped

### `/user/password/reset`

- Methods: `GET, POST`
- Sources: `platform_frontend`
- Description: Reset password. / Discovered from platform frontend bundle.
- Safe probe: `False`
- Request body: Account mutation.
- Probe: skipped

### `/user/token`

- Methods: `GET, POST`
- Sources: `platform_frontend`
- Description: User token endpoint. / Discovered from platform frontend bundle.
- Safe probe: `False`
- Request body: Token operation.
- Probe: skipped

### `/users`

- Methods: `GET`
- Sources: `platform_frontend`
- Description: Users collection. / Discovered from platform frontend bundle.
- Safe probe: `True`
- Params: `{"limit": "optional"}`
- Probe URL: `https://api.worldquantbrain.com/users`
- OPTIONS: `{"status_code": 200, "allow": "POST, OPTIONS", "content_type": "application/json"}`
- Allowed methods: `POST, OPTIONS`
- Probe status: `405 Method Not Allowed`
- Usable GET: `False`
- Response shape: `{"detail": "str"}`

### `/users/self`

- Methods: `GET`
- Sources: `rocky-d/wqb`
- Description: Current user profile.
- Safe probe: `True`
- Probe URL: `https://api.worldquantbrain.com/users/self`
- OPTIONS: `{"status_code": 200, "allow": "GET, PUT, PATCH, DELETE, HEAD, OPTIONS", "content_type": "application/json"}`
- Allowed methods: `GET, PUT, PATCH, DELETE, HEAD, OPTIONS`
- Probe status: `200 OK`
- Usable GET: `True`
- Response shape: `{"id": "str", "email": "str", "telephone": "str", "firstName": "str", "lastName": "str", "fullName": "str", "gender": "str", "dateCreated": "str", "dateVerified": "str", "dateApproved": "str", "verified": "bool", "approved": "bool", "address": {"street": "NoneType", "city": "str", "state": "NoneType", "postalCode": "NoneType", "country": "str"}, "education": {"university": "str", "major": "str", "degree": "str", "stem": "bool", "graduationYear": "int", "gpa": "float", "maxGPA": "float"}, "employment": "NoneType", "recruitment": {"englishProficiency": "str", "codingProficiency": "str", "roleInterest": ["str"]}, "resume": {"dateCreated": "str"}, "image": {"url": "str"}, "settings": {"allowTracking": "bool", "communication": {"allowSMS": "bool"}, "privacy": {"name": {"visibility": "...", "moderation": "..."}, "image": {"visibility": "...", "moderation": "..."}}, "client": {}}, "onboarding": {"status": "str"}, "auxiliary": {"campaign": {"campaign": "str", "source": "str", "medium": "str", "term": "NoneType", "content": "str"}}, "geniusLevel": "str"}`

### `/users/self/achievements`

- Methods: `GET`
- Sources: `platform_dynamic_capture`
- Description: Observed by passive platform network capture.
- Safe probe: `True`
- Probe skipped/error: `Observed by platform dynamic network capture; no separate safe probe was run.`

### `/users/self/activities/pyramid-alphas`

- Methods: `GET`
- Sources: `observed_platform`
- Description: Current user's pyramid alpha counts.
- Safe probe: `True`
- Params: `{"startDate": "YYYY-MM-DD", "endDate": "YYYY-MM-DD"}`
- Probe URL: `https://api.worldquantbrain.com/users/self/activities/pyramid-alphas`
- OPTIONS: `{"status_code": 405, "allow": "GET, HEAD, OPTIONS", "content_type": "application/json"}`
- Allowed methods: `GET, HEAD, OPTIONS`
- Probe status: `200 OK`
- Usable GET: `True`
- Response shape: `{"pyramids": [{"category": {"id": "...", "name": "..."}, "region": "str", "delay": "int", "alphaCount": "int"}]}`

### `/users/self/activities/pyramid-multipliers`

- Methods: `GET`
- Sources: `observed_platform`
- Description: Current user's pyramid multipliers.
- Safe probe: `True`
- Probe URL: `https://api.worldquantbrain.com/users/self/activities/pyramid-multipliers`
- OPTIONS: `{"status_code": 405, "allow": "GET, HEAD, OPTIONS", "content_type": "application/json"}`
- Allowed methods: `GET, HEAD, OPTIONS`
- Probe status: `200 OK`
- Usable GET: `True`
- Response shape: `{"pyramids": [{"category": {"id": "...", "name": "..."}, "region": "str", "delay": "int", "multiplier": "float"}]}`

### `/users/self/activities/simulations`

- Methods: `GET`
- Sources: `platform_dynamic_capture`
- Description: Observed by passive platform network capture.
- Safe probe: `True`
- Params: `{"date>": "observed query parameter"}`
- Probe skipped/error: `Observed by platform dynamic network capture; no separate safe probe was run.`

### `/users/self/agreements`

- Methods: `GET`
- Sources: `platform_dynamic_capture`
- Description: Observed by passive platform network capture.
- Safe probe: `True`
- Probe skipped/error: `Observed by platform dynamic network capture; no separate safe probe was run.`

### `/users/self/alphas`

- Methods: `GET`
- Sources: `rocky-d/wqb`
- Description: Current user's alphas.
- Safe probe: `True`
- Params: `{"limit": "1..100", "offset": "0..10000", "dateSubmitted": "range", "type": "REGULAR|SUPER", "color": "platform color", "tag": "tag filter"}`
- Probe URL: `https://api.worldquantbrain.com/users/self/alphas?limit=1`
- OPTIONS: `{"status_code": 200, "allow": "GET, HEAD, OPTIONS", "content_type": "application/json"}`
- Allowed methods: `GET, HEAD, OPTIONS`
- Probe status: `200 OK`
- Usable GET: `True`
- Response shape: `{"count": "int", "next": "str", "previous": "NoneType", "results": [{"id": "str", "type": "str", "author": "str", "settings": {"instrumentType": "...", "region": "...", "universe": "...", "delay": "...", "decay": "...", "neutralization": "...", "truncation": "...", "pasteurization": "...", "unitHandling": "...", "nanHandling": "...", "maxTrade": "...", "maxPosition": "...", "language": "...", "visualization": "...", "startDate": "...", "endDate": "...", "testPeriod": "..."}, "regular": {"code": "...", "description": "...", "operatorCount": "..."}, "dateCreated": "str", "dateSubmitted": "NoneType", "dateModified": "str", "name": "NoneType", "favorite": "bool", "hidden": "bool", "color": "NoneType", "category": "NoneType", "tags": [], "classifications": ["..."], "grade": "NoneType", "stage": "str", "status": "str", "is": {"pnl": "...", "bookSize": "...", "longCount": "...", "shortCount": "...", "turnover": "...", "returns": "...", "drawdown": "...", "margin": "...", "sharpe": "...", "fitness": "...", "startDate": "...", "investabilityConstrained": "...", "riskNeutralized": "...", "checks": "..."}, "os": "NoneType", "train": {"pnl": "...", "bookSize": "...", "longCount": "...", "short`

### `/users/self/alphas/summary`

- Methods: `GET`
- Sources: `platform_dynamic_capture`
- Description: Observed by passive platform network capture.
- Safe probe: `True`
- Probe skipped/error: `Observed by platform dynamic network capture; no separate safe probe was run.`

### `/users/self/consultant/summary`

- Methods: `GET`
- Sources: `platform_dynamic_capture, platform_frontend`
- Description: Current consultant performance summary.
- Safe probe: `True`
- Probe URL: `https://api.worldquantbrain.com/users/self/consultant/summary`
- OPTIONS: `{"status_code": 405, "allow": "GET, HEAD, OPTIONS", "content_type": "application/json"}`
- Allowed methods: `GET, HEAD, OPTIONS`
- Probe status: `200 OK`
- Usable GET: `True`
- Response shape: `{"performance": {"currentLevel": "str", "bestLevel": "str", "currentQuarter": {"name": "str", "startDate": "str", "endDate": "str"}, "current": {"level": "NoneType", "geniusLevel": "str", "quarter": {"name": "...", "startDate": "...", "endDate": "..."}, "alphaCount": "int", "pyramidCount": "int", "combinedSelectedAlphaPerformance": "float", "combinedAlphaPerformance": "float", "operatorCount": "int", "operatorAvg": "float", "fieldCount": "int", "fieldAvg": "float", "communityActivity": "float", "maxSimulationStreak": "int", "extras": [], "combinedPowerPoolAlphaPerformance": "float", "combinedOsmosisPerformance": "float"}, "previous": {"level": "str", "geniusLevel": "str", "quarter": {"name": "...", "startDate": "...", "endDate": "..."}, "alphaCount": "int", "pyramidCount": "int", "combinedSelectedAlphaPerformance": "float", "combinedAlphaPerformance": "float", "operatorCount": "int", "operatorAvg": "float", "fieldCount": "int", "fieldAvg": "float", "communityActivity": "float", "maxSimulationStreak": "int", "extras": [], "combinedPowerPoolAlphaPerformance": "float", "combinedOsmosisPerformance": "float"}, "history": [{"level": "...", "geniusLevel": "...", "quarter": "...", "alphaCo`

### `/users/self/consultant/tutorial/summary`

- Methods: `GET, PATCH`
- Sources: `platform_dynamic_capture`
- Description: Observed by passive platform network capture.
- Safe probe: `False`
- Request body: Observed request body shape in dynamic_capture.
- Probe skipped/error: `Observed by platform dynamic network capture; no separate safe probe was run.`

### `/users/self/messages`

- Methods: `GET`
- Sources: `observed_platform, platform_dynamic_capture`
- Description: Current user's messages.
- Safe probe: `True`
- Params: `{"limit": "optional", "offset": "optional", "order": "observed query parameter", "type": "observed query parameter"}`
- Probe URL: `https://api.worldquantbrain.com/users/self/messages`
- OPTIONS: `{"status_code": 405, "allow": "GET, HEAD, OPTIONS", "content_type": "application/json"}`
- Allowed methods: `GET, HEAD, OPTIONS`
- Probe status: `200 OK`
- Usable GET: `True`
- Response shape: `{"count": "int", "next": "str", "previous": "NoneType", "results": [{"id": "str", "type": "str", "title": "str", "description": "str", "dateCreated": "str", "tags": [], "read": "bool"}]}`

### `/users/self/messages/summary`

- Methods: `GET`
- Sources: `platform_dynamic_capture`
- Description: Observed by passive platform network capture.
- Safe probe: `True`
- Probe skipped/error: `Observed by platform dynamic network capture; no separate safe probe was run.`

### `/users/self/pyramid/alphas`

- Methods: `GET`
- Sources: `observed_platform`
- Description: Fallback pyramid alpha endpoint.
- Safe probe: `True`
- Params: `{"startDate": "YYYY-MM-DD", "endDate": "YYYY-MM-DD"}`
- Probe URL: `https://api.worldquantbrain.com/users/self/pyramid/alphas`
- OPTIONS: `{"status_code": 404, "allow": null, "content_type": "application/json"}`
- Probe status: `404 Not Found`
- Usable GET: `False`
- Response shape: `{"detail": "str"}`

### `/users/self/teams`

- Methods: `GET`
- Sources: `platform_dynamic_capture`
- Description: Observed by passive platform network capture.
- Safe probe: `True`
- Params: `{"members.self.status": "observed query parameter", "order": "observed query parameter", "status": "observed query parameter"}`
- Probe skipped/error: `Observed by platform dynamic network capture; no separate safe probe was run.`

### `/users/self/tutorial/steps`

- Methods: `GET`
- Sources: `platform_frontend`
- Description: Tutorial step state. / Discovered from platform frontend bundle.
- Safe probe: `True`
- Probe URL: `https://api.worldquantbrain.com/users/self/tutorial/steps`
- OPTIONS: `{"status_code": 200, "allow": "GET, HEAD, OPTIONS", "content_type": "application/json"}`
- Allowed methods: `GET, HEAD, OPTIONS`
- Probe status: `200 OK`
- Usable GET: `True`
- Response shape: `[{"name": "str", "task": "str", "hint": "str", "answer": "str", "slug": "str", "stepIndex": "int"}]`

### `/users/self/tutorial/summary`

- Methods: `GET`
- Sources: `platform_frontend`
- Description: Tutorial summary state. / Discovered from platform frontend bundle.
- Safe probe: `True`
- Probe URL: `https://api.worldquantbrain.com/users/self/tutorial/summary`
- OPTIONS: `{"status_code": 200, "allow": "GET, POST, PATCH, HEAD, OPTIONS", "content_type": "application/json"}`
- Allowed methods: `GET, POST, PATCH, HEAD, OPTIONS`
- Probe status: `200 OK`
- Usable GET: `True`
- Response shape: `{"active": "bool", "expired": "bool", "startDatetime": "NoneType", "completionDate": "NoneType", "expireDatetime": "NoneType", "currentStep": "NoneType", "maxUnlockedStep": "NoneType", "totalSteps": "int", "status": "NoneType", "notificationSlug": "NoneType"}`

### `/users/{user_id}`

- Methods: `GET`
- Sources: `platform_dynamic_capture, rocky-d/wqb`
- Description: User profile by id.
- Safe probe: `False`
- Probe: skipped

### `/users/{user_id}/achievements`

- Methods: `GET`
- Sources: `platform_dynamic_capture`
- Description: Observed by passive platform network capture.
- Safe probe: `True`
- Probe skipped/error: `Observed by platform dynamic network capture; no separate safe probe was run.`

### `/users/{user_id}/activities`

- Methods: `GET`
- Sources: `observed_platform`
- Description: User activities by id.
- Safe probe: `False`
- Probe: skipped

### `/users/{user_id}/alphas`

- Methods: `OPTIONS`
- Sources: `platform_dynamic_capture`
- Description: Observed by passive platform network capture.
- Safe probe: `True`
- Probe skipped/error: `Observed by platform dynamic network capture; no separate safe probe was run.`

### `/users/{user_id}/competitions`

- Methods: `GET`
- Sources: `observed_platform, platform_dynamic_capture`
- Description: User competitions by id.
- Safe probe: `False`
- Probe: skipped

### `/users/{user_id}/settings/simulation`

- Methods: `GET`
- Sources: `platform_dynamic_capture`
- Description: Observed by passive platform network capture.
- Safe probe: `True`
- Probe skipped/error: `Observed by platform dynamic network capture; no separate safe probe was run.`

### `/video-courses`

- Methods: `GET`
- Sources: `platform_frontend`
- Description: Video courses. / Discovered from platform frontend bundle.
- Safe probe: `True`
- Probe URL: `https://api.worldquantbrain.com/video-courses`
- OPTIONS: `{"status_code": 200, "allow": "GET, HEAD, OPTIONS", "content_type": "application/json"}`
- Allowed methods: `GET, HEAD, OPTIONS`
- Probe status: `200 OK`
- Usable GET: `True`
- Response shape: `{"count": "int", "next": "str", "previous": "NoneType", "results": [{"id": "str", "category": "str", "videos": ["..."], "title": "str", "sequence": "int", "description": "str", "lastModified": "str"}]}`
