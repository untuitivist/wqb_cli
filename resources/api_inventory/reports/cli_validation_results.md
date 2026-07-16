# CLI Validation Results

- Generated at: `2026-07-16T08:57:52+00:00`
- Endpoint count: `109`
- Method cases: `134`
- Show checks: `109`
- Command checks: `134`
- Safe calls executed: `110`
- Mutating requests: `24`
- CLI errors: `0`

## Results

### `GET /achievements`

- Show OK: `True`
- Check OK: `True`
- Executed: `True`
- HTTP: `200 OK`

### `GET /achievements/{achievement_id}/icon`

- Show OK: `True`
- Check OK: `True`
- Executed: `True`
- HTTP: `200 OK`

### `GET /agreements`

- Show OK: `True`
- Check OK: `True`
- Executed: `True`
- HTTP: `405 Method Not Allowed`

### `GET /alphas`

- Show OK: `True`
- Check OK: `True`
- Executed: `True`
- HTTP: `405 Method Not Allowed`

### `GET /alphas/distribution`

- Show OK: `True`
- Check OK: `True`
- Executed: `True`
- HTTP: `404 Not Found`

### `GET /alphas/lists`

- Show OK: `True`
- Check OK: `True`
- Executed: `True`
- HTTP: `404 Not Found`

### `GET /alphas/sample-alpha-id-walkthrough`

- Show OK: `True`
- Check OK: `True`
- Executed: `True`
- HTTP: `404 Not Found`

### `GET /alphas/super-selection`

- Show OK: `True`
- Check OK: `True`
- Executed: `True`
- HTTP: `404 Not Found`

### `GET /alphas/unsubmitted`

- Show OK: `True`
- Check OK: `True`
- Executed: `True`
- HTTP: `404 Not Found`

### `GET /alphas/{alpha_id}`

- Show OK: `True`
- Check OK: `True`
- Executed: `True`
- HTTP: `200 OK`

### `PATCH /alphas/{alpha_id}`

- Show OK: `True`
- Check OK: `True`
- Executed: `False`
- Reason: mutating method requires

### `GET /alphas/{alpha_id}/alphas`

- Show OK: `True`
- Check OK: `True`
- Executed: `True`
- HTTP: `404 Not Found`

### `GET /alphas/{alpha_id}/check`

- Show OK: `True`
- Check OK: `True`
- Executed: `True`
- HTTP: `200 OK`

### `GET /alphas/{alpha_id}/correlations`

- Show OK: `True`
- Check OK: `True`
- Executed: `True`
- HTTP: `404 Not Found`

### `GET /alphas/{alpha_id}/correlations/power-pool`

- Show OK: `True`
- Check OK: `True`
- Executed: `True`
- HTTP: `200 OK`

### `GET /alphas/{alpha_id}/correlations/prod`

- Show OK: `True`
- Check OK: `True`
- Executed: `True`
- HTTP: `200 OK`

### `GET /alphas/{alpha_id}/correlations/self`

- Show OK: `True`
- Check OK: `True`
- Executed: `True`
- HTTP: `200 OK`

### `GET /alphas/{alpha_id}/performance-comparison`

- Show OK: `True`
- Check OK: `True`
- Executed: `True`
- HTTP: `404 Not Found`

### `GET /alphas/{alpha_id}/recordsets`

- Show OK: `True`
- Check OK: `True`
- Executed: `True`
- HTTP: `200 OK`

### `GET /alphas/{alpha_id}/recordsets/pnl`

- Show OK: `True`
- Check OK: `True`
- Executed: `True`
- HTTP: `200 OK`

### `GET /alphas/{alpha_id}/recordsets/sharpe`

- Show OK: `True`
- Check OK: `True`
- Executed: `True`
- HTTP: `200 OK`

### `GET /alphas/{alpha_id}/recordsets/yearly-stats`

- Show OK: `True`
- Check OK: `True`
- Executed: `True`
- HTTP: `200 OK`

### `GET /alphas/{alpha_id}/recordsets/{record_set_name}`

- Show OK: `True`
- Check OK: `True`
- Executed: `True`
- HTTP: `200 OK`

### `POST /alphas/{alpha_id}/submit`

- Show OK: `True`
- Check OK: `True`
- Executed: `False`
- Reason: mutating method requires

### `DELETE /authentication`

- Show OK: `True`
- Check OK: `True`
- Executed: `False`
- Reason: mutating method requires

### `GET /authentication`

- Show OK: `True`
- Check OK: `True`
- Executed: `True`
- HTTP: `200 OK`

### `HEAD /authentication`

- Show OK: `True`
- Check OK: `True`
- Executed: `True`
- HTTP: `200 OK`

### `POST /authentication`

- Show OK: `True`
- Check OK: `True`
- Executed: `False`
- Reason: mutating method requires

### `GET /authentication/brainlabs`

- Show OK: `True`
- Check OK: `True`
- Executed: `True`
- HTTP: `302 Found`

### `GET /authentication/persona`

- Show OK: `True`
- Check OK: `True`
- Executed: `True`
- HTTP: `400 Bad Request`

### `GET /authentication/support`

- Show OK: `True`
- Check OK: `True`
- Executed: `True`
- HTTP: `302 Found`

### `GET /authentication/workday`

- Show OK: `True`
- Check OK: `True`
- Executed: `True`
- HTTP: `302 Found`

### `GET /captcha`

- Show OK: `True`
- Check OK: `True`
- Executed: `True`
- HTTP: `200 OK`

### `GET /competition-levels`

- Show OK: `True`
- Check OK: `True`
- Executed: `True`
- HTTP: `200 OK`

### `GET /competition-levels/{competition_level_id}/icon`

- Show OK: `True`
- Check OK: `True`
- Executed: `True`
- HTTP: `200 OK`

### `GET /competitions`

- Show OK: `True`
- Check OK: `True`
- Executed: `True`
- HTTP: `200 OK`

### `GET /competitions/{competition_id}`

- Show OK: `True`
- Check OK: `True`
- Executed: `True`
- HTTP: `200 OK`

### `GET /competitions/{competition_id}/agreement`

- Show OK: `True`
- Check OK: `True`
- Executed: `True`
- HTTP: `200 OK`

### `POST /competitions/{competition_id}/agreement`

- Show OK: `True`
- Check OK: `True`
- Executed: `False`
- Reason: mutating method requires

### `GET /configuration`

- Show OK: `True`
- Check OK: `True`
- Executed: `True`
- HTTP: `200 OK`

### `GET /consultant`

- Show OK: `True`
- Check OK: `True`
- Executed: `True`
- HTTP: `404 Not Found`

### `GET /consultant-datasets`

- Show OK: `True`
- Check OK: `True`
- Executed: `True`
- HTTP: `404 Not Found`

### `GET /consultant-information/consultant-dos-and-donts`

- Show OK: `True`
- Check OK: `True`
- Executed: `True`
- HTTP: `404 Not Found`

### `GET /consultant-information/consultant-faqs`

- Show OK: `True`
- Check OK: `True`
- Executed: `True`
- HTTP: `404 Not Found`

### `GET /consultant-information/osmosis-allocation-guide-consultants`

- Show OK: `True`
- Check OK: `True`
- Executed: `True`
- HTTP: `404 Not Found`

### `GET /consultant-information/visualization-tool`

- Show OK: `True`
- Check OK: `True`
- Executed: `True`
- HTTP: `404 Not Found`

### `GET /consultant-program`

- Show OK: `True`
- Check OK: `True`
- Executed: `True`
- HTTP: `404 Not Found`

### `GET /consultant-program/{language}`

- Show OK: `True`
- Check OK: `True`
- Executed: `True`
- HTTP: `404 Not Found`

### `GET /consultant/boards`

- Show OK: `True`
- Check OK: `True`
- Executed: `True`
- HTTP: `404 Not Found`

### `GET /consultant/boards/leader`

- Show OK: `True`
- Check OK: `True`
- Executed: `True`
- HTTP: `200 OK`

### `GET /consultant/summary`

- Show OK: `True`
- Check OK: `True`
- Executed: `True`
- HTTP: `404 Not Found`

### `GET /data-categories`

- Show OK: `True`
- Check OK: `True`
- Executed: `True`
- HTTP: `200 OK`

### `GET /data-fields`

- Show OK: `True`
- Check OK: `True`
- Executed: `True`
- HTTP: `200 OK`

### `GET /data-fields/summary`

- Show OK: `True`
- Check OK: `True`
- Executed: `True`
- HTTP: `200 OK`

### `GET /data-fields/{field_id}`

- Show OK: `True`
- Check OK: `True`
- Executed: `True`
- HTTP: `200 OK`

### `GET /data-sets`

- Show OK: `True`
- Check OK: `True`
- Executed: `True`
- HTTP: `200 OK`

### `GET /data-sets/search`

- Show OK: `True`
- Check OK: `True`
- Executed: `True`
- HTTP: `400 Bad Request`

### `POST /data-sets/search`

- Show OK: `True`
- Check OK: `True`
- Executed: `False`
- Reason: mutating method requires

### `GET /data-sets/{dataset_id}`

- Show OK: `True`
- Check OK: `True`
- Executed: `True`
- HTTP: `200 OK`

### `POST /errors/api/2/envelope`

- Show OK: `True`
- Check OK: `True`
- Executed: `False`
- Reason: mutating method requires

### `GET /events`

- Show OK: `True`
- Check OK: `True`
- Executed: `True`
- HTTP: `200 OK`

### `OPTIONS /events`

- Show OK: `True`
- Check OK: `True`
- Executed: `True`
- HTTP: `200 OK`

### `GET /events/{event_id}`

- Show OK: `True`
- Check OK: `True`
- Executed: `True`
- HTTP: `200 OK`

### `GET /messages`

- Show OK: `True`
- Check OK: `True`
- Executed: `True`
- HTTP: `404 Not Found`

### `GET /operators`

- Show OK: `True`
- Check OK: `True`
- Executed: `True`
- HTTP: `200 OK`

### `GET /search`

- Show OK: `True`
- Check OK: `True`
- Executed: `True`
- HTTP: `400 Bad Request`

### `GET /simulations`

- Show OK: `True`
- Check OK: `True`
- Executed: `True`
- HTTP: `405 Method Not Allowed`

### `OPTIONS /simulations`

- Show OK: `True`
- Check OK: `True`
- Executed: `True`
- HTTP: `200 OK`

### `POST /simulations`

- Show OK: `True`
- Check OK: `True`
- Executed: `False`
- Reason: mutating method requires

### `GET /simulations/super-selection`

- Show OK: `True`
- Check OK: `True`
- Executed: `True`
- HTTP: `200 OK`

### `POST /simulations/super-selection`

- Show OK: `True`
- Check OK: `True`
- Executed: `False`
- Reason: mutating method requires

### `GET /simulations/{simulation_id}`

- Show OK: `True`
- Check OK: `True`
- Executed: `True`
- HTTP: `200 OK`

### `GET /suggest/examples`

- Show OK: `True`
- Check OK: `True`
- Executed: `True`
- HTTP: `200 OK`

### `POST /suggest/examples`

- Show OK: `True`
- Check OK: `True`
- Executed: `False`
- Reason: mutating method requires

### `GET /suggest/expression`

- Show OK: `True`
- Check OK: `True`
- Executed: `True`
- HTTP: `404 Not Found`

### `POST /suggest/expression`

- Show OK: `True`
- Check OK: `True`
- Executed: `False`
- Reason: mutating method requires

### `GET /suggest/fastexpr`

- Show OK: `True`
- Check OK: `True`
- Executed: `True`
- HTTP: `404 Not Found`

### `POST /suggest/fastexpr`

- Show OK: `True`
- Check OK: `True`
- Executed: `False`
- Reason: mutating method requires

### `GET /suggest/fields`

- Show OK: `True`
- Check OK: `True`
- Executed: `True`
- HTTP: `200 OK`

### `POST /suggest/fields`

- Show OK: `True`
- Check OK: `True`
- Executed: `False`
- Reason: mutating method requires

### `GET /tags`

- Show OK: `True`
- Check OK: `True`
- Executed: `True`
- HTTP: `200 OK`

### `GET /teams`

- Show OK: `True`
- Check OK: `True`
- Executed: `True`
- HTTP: `405 Method Not Allowed`

### `GET /tutorial-pages`

- Show OK: `True`
- Check OK: `True`
- Executed: `True`
- HTTP: `404 Not Found`

### `GET /tutorial-pages/{page_id}`

- Show OK: `True`
- Check OK: `True`
- Executed: `True`
- HTTP: `404 Not Found`

### `GET /tutorial/{tutorial_slug}`

- Show OK: `True`
- Check OK: `True`
- Executed: `True`
- HTTP: `200 OK`

### `GET /tutorials`

- Show OK: `True`
- Check OK: `True`
- Executed: `True`
- HTTP: `200 OK`

### `GET /user/email/change`

- Show OK: `True`
- Check OK: `True`
- Executed: `True`
- HTTP: `405 Method Not Allowed`

### `POST /user/email/change`

- Show OK: `True`
- Check OK: `True`
- Executed: `False`
- Reason: mutating method requires

### `GET /user/email/reverify`

- Show OK: `True`
- Check OK: `True`
- Executed: `True`
- HTTP: `405 Method Not Allowed`

### `POST /user/email/reverify`

- Show OK: `True`
- Check OK: `True`
- Executed: `False`
- Reason: mutating method requires

### `GET /user/email/verify`

- Show OK: `True`
- Check OK: `True`
- Executed: `True`
- HTTP: `405 Method Not Allowed`

### `POST /user/email/verify`

- Show OK: `True`
- Check OK: `True`
- Executed: `False`
- Reason: mutating method requires

### `GET /user/password/change`

- Show OK: `True`
- Check OK: `True`
- Executed: `True`
- HTTP: `405 Method Not Allowed`

### `POST /user/password/change`

- Show OK: `True`
- Check OK: `True`
- Executed: `False`
- Reason: mutating method requires

### `GET /user/password/forgot`

- Show OK: `True`
- Check OK: `True`
- Executed: `True`
- HTTP: `405 Method Not Allowed`

### `POST /user/password/forgot`

- Show OK: `True`
- Check OK: `True`
- Executed: `False`
- Reason: mutating method requires

### `GET /user/password/reset`

- Show OK: `True`
- Check OK: `True`
- Executed: `True`
- HTTP: `405 Method Not Allowed`

### `POST /user/password/reset`

- Show OK: `True`
- Check OK: `True`
- Executed: `False`
- Reason: mutating method requires

### `GET /user/token`

- Show OK: `True`
- Check OK: `True`
- Executed: `True`
- HTTP: `405 Method Not Allowed`

### `POST /user/token`

- Show OK: `True`
- Check OK: `True`
- Executed: `False`
- Reason: mutating method requires

### `GET /users`

- Show OK: `True`
- Check OK: `True`
- Executed: `True`
- HTTP: `405 Method Not Allowed`

### `GET /users/self`

- Show OK: `True`
- Check OK: `True`
- Executed: `True`
- HTTP: `200 OK`

### `GET /users/self/achievements`

- Show OK: `True`
- Check OK: `True`
- Executed: `True`
- HTTP: `200 OK`

### `GET /users/self/activities/pyramid-alphas`

- Show OK: `True`
- Check OK: `True`
- Executed: `True`
- HTTP: `200 OK`

### `GET /users/self/activities/pyramid-multipliers`

- Show OK: `True`
- Check OK: `True`
- Executed: `True`
- HTTP: `200 OK`

### `GET /users/self/activities/simulations`

- Show OK: `True`
- Check OK: `True`
- Executed: `True`
- HTTP: `200 OK`

### `GET /users/self/agreements`

- Show OK: `True`
- Check OK: `True`
- Executed: `True`
- HTTP: `200 OK`

### `GET /users/self/alphas`

- Show OK: `True`
- Check OK: `True`
- Executed: `True`
- HTTP: `200 OK`

### `GET /users/self/alphas/summary`

- Show OK: `True`
- Check OK: `True`
- Executed: `True`
- HTTP: `200 OK`

### `GET /users/self/consultant/summary`

- Show OK: `True`
- Check OK: `True`
- Executed: `True`
- HTTP: `200 OK`

### `GET /users/self/consultant/tutorial/summary`

- Show OK: `True`
- Check OK: `True`
- Executed: `True`
- HTTP: `200 OK`

### `PATCH /users/self/consultant/tutorial/summary`

- Show OK: `True`
- Check OK: `True`
- Executed: `False`
- Reason: mutating method requires

### `GET /users/self/messages`

- Show OK: `True`
- Check OK: `True`
- Executed: `True`
- HTTP: `200 OK`

### `GET /users/self/messages/summary`

- Show OK: `True`
- Check OK: `True`
- Executed: `True`
- HTTP: `200 OK`

### `GET /users/self/pyramid/alphas`

- Show OK: `True`
- Check OK: `True`
- Executed: `True`
- HTTP: `404 Not Found`

### `GET /users/self/teams`

- Show OK: `True`
- Check OK: `True`
- Executed: `True`
- HTTP: `200 OK`

### `GET /users/self/tutorial/steps`

- Show OK: `True`
- Check OK: `True`
- Executed: `True`
- HTTP: `200 OK`

### `GET /users/self/tutorial/summary`

- Show OK: `True`
- Check OK: `True`
- Executed: `True`
- HTTP: `200 OK`

### `GET /users/{user_id}`

- Show OK: `True`
- Check OK: `True`
- Executed: `True`
- HTTP: `200 OK`

### `GET /users/{user_id}/achievements`

- Show OK: `True`
- Check OK: `True`
- Executed: `True`
- HTTP: `200 OK`

### `GET /users/{user_id}/activities`

- Show OK: `True`
- Check OK: `True`
- Executed: `True`
- HTTP: `200 OK`

### `GET /users/{user_id}/activities/diversity`

- Show OK: `True`
- Check OK: `True`
- Executed: `True`
- HTTP: `200 OK`

### `OPTIONS /users/{user_id}/alphas`

- Show OK: `True`
- Check OK: `True`
- Executed: `True`
- HTTP: `200 OK`

### `GET /users/{user_id}/competitions`

- Show OK: `True`
- Check OK: `True`
- Executed: `True`
- HTTP: `200 OK`

### `GET /users/{user_id}/settings/simulation`

- Show OK: `True`
- Check OK: `True`
- Executed: `True`
- HTTP: `200 OK`

### `GET /video-courses`

- Show OK: `True`
- Check OK: `True`
- Executed: `True`
- HTTP: `200 OK`

### `GET /competitions/{competition_id}/boards/{board_type}`

- Show OK: `True`
- Check OK: `True`
- Executed: `True`
- HTTP: `200 OK`

### `GET /competitions/spc/submissions`

- Show OK: `True`
- Check OK: `True`
- Executed: `True`
- HTTP: `200 OK`

### `POST /competitions/spc/submissions`

- Show OK: `True`
- Check OK: `True`
- Executed: `False`
- Reason: mutating method not executed during validation

### `GET /competitions/spc/submissions/{submission_id}`

- Show OK: `True`
- Check OK: `True`
- Executed: `True`
- HTTP: `200 OK`

### `PUT /competitions/spc/submissions/{submission_id}`

- Show OK: `True`
- Check OK: `True`
- Executed: `False`
- Reason: mutating method not executed during validation

### `PATCH /competitions/spc/submissions/{submission_id}`

- Show OK: `True`
- Check OK: `True`
- Executed: `False`
- Reason: mutating method not executed during validation

### `GET /consultant/boards/{board_type}`

- Show OK: `True`
- Check OK: `True`
- Executed: `True`
- HTTP: `200 OK`

### `GET /consultant/boards/spc`

- Show OK: `True`
- Check OK: `True`
- Executed: `True`
- HTTP: `200 OK`
