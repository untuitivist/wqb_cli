# CLI Validation Results

- Generated at: `2026-05-18T17:45:12.249392+00:00`
- Endpoint count: `104`
- Method cases: `126`
- Show checks: `104`
- Dry-run checks: `126`
- Safe calls executed: `105`
- Mutating dry-run only: `21`
- CLI errors: `0`

## Results

### `GET /achievements`

- Show OK: `True`
- Dry-run OK: `True`
- Executed: `True`
- HTTP: `200 OK`

### `GET /achievements/{achievement_id}/icon`

- Show OK: `True`
- Dry-run OK: `True`
- Executed: `True`
- HTTP: `200 OK`

### `GET /agreements`

- Show OK: `True`
- Dry-run OK: `True`
- Executed: `True`
- HTTP: `405 Method Not Allowed`

### `GET /alphas`

- Show OK: `True`
- Dry-run OK: `True`
- Executed: `True`
- HTTP: `405 Method Not Allowed`

### `GET /alphas/distribution`

- Show OK: `True`
- Dry-run OK: `True`
- Executed: `True`
- HTTP: `404 Not Found`

### `GET /alphas/lists`

- Show OK: `True`
- Dry-run OK: `True`
- Executed: `True`
- HTTP: `404 Not Found`

### `GET /alphas/sample-alpha-id-walkthrough`

- Show OK: `True`
- Dry-run OK: `True`
- Executed: `True`
- HTTP: `404 Not Found`

### `GET /alphas/super-selection`

- Show OK: `True`
- Dry-run OK: `True`
- Executed: `True`
- HTTP: `404 Not Found`

### `GET /alphas/unsubmitted`

- Show OK: `True`
- Dry-run OK: `True`
- Executed: `True`
- HTTP: `404 Not Found`

### `GET /alphas/{alpha_id}`

- Show OK: `True`
- Dry-run OK: `True`
- Executed: `True`
- HTTP: `200 OK`

### `PATCH /alphas/{alpha_id}`

- Show OK: `True`
- Dry-run OK: `True`
- Executed: `False`
- Reason: mutating method verified as dry-run only without --execute

### `GET /alphas/{alpha_id}/alphas`

- Show OK: `True`
- Dry-run OK: `True`
- Executed: `True`
- HTTP: `404 Not Found`

### `GET /alphas/{alpha_id}/check`

- Show OK: `True`
- Dry-run OK: `True`
- Executed: `True`
- HTTP: `200 OK`

### `GET /alphas/{alpha_id}/correlations`

- Show OK: `True`
- Dry-run OK: `True`
- Executed: `True`
- HTTP: `404 Not Found`

### `GET /alphas/{alpha_id}/correlations/power-pool`

- Show OK: `True`
- Dry-run OK: `True`
- Executed: `True`
- HTTP: `200 OK`

### `GET /alphas/{alpha_id}/correlations/prod`

- Show OK: `True`
- Dry-run OK: `True`
- Executed: `True`
- HTTP: `200 OK`

### `GET /alphas/{alpha_id}/correlations/self`

- Show OK: `True`
- Dry-run OK: `True`
- Executed: `True`
- HTTP: `200 OK`

### `GET /alphas/{alpha_id}/performance-comparison`

- Show OK: `True`
- Dry-run OK: `True`
- Executed: `True`
- HTTP: `404 Not Found`

### `GET /alphas/{alpha_id}/recordsets`

- Show OK: `True`
- Dry-run OK: `True`
- Executed: `True`
- HTTP: `200 OK`

### `GET /alphas/{alpha_id}/recordsets/pnl`

- Show OK: `True`
- Dry-run OK: `True`
- Executed: `True`
- HTTP: `200 OK`

### `GET /alphas/{alpha_id}/recordsets/sharpe`

- Show OK: `True`
- Dry-run OK: `True`
- Executed: `True`
- HTTP: `200 OK`

### `GET /alphas/{alpha_id}/recordsets/yearly-stats`

- Show OK: `True`
- Dry-run OK: `True`
- Executed: `True`
- HTTP: `200 OK`

### `GET /alphas/{alpha_id}/recordsets/{record_set_name}`

- Show OK: `True`
- Dry-run OK: `True`
- Executed: `True`
- HTTP: `200 OK`

### `POST /alphas/{alpha_id}/submit`

- Show OK: `True`
- Dry-run OK: `True`
- Executed: `False`
- Reason: mutating method verified as dry-run only without --execute

### `DELETE /authentication`

- Show OK: `True`
- Dry-run OK: `True`
- Executed: `False`
- Reason: mutating method verified as dry-run only without --execute

### `GET /authentication`

- Show OK: `True`
- Dry-run OK: `True`
- Executed: `True`
- HTTP: `200 OK`

### `HEAD /authentication`

- Show OK: `True`
- Dry-run OK: `True`
- Executed: `True`
- HTTP: `200 OK`

### `POST /authentication`

- Show OK: `True`
- Dry-run OK: `True`
- Executed: `False`
- Reason: mutating method verified as dry-run only without --execute

### `GET /authentication/brainlabs`

- Show OK: `True`
- Dry-run OK: `True`
- Executed: `True`
- HTTP: `302 Found`

### `GET /authentication/persona`

- Show OK: `True`
- Dry-run OK: `True`
- Executed: `True`
- HTTP: `400 Bad Request`

### `GET /authentication/support`

- Show OK: `True`
- Dry-run OK: `True`
- Executed: `True`
- HTTP: `302 Found`

### `GET /authentication/workday`

- Show OK: `True`
- Dry-run OK: `True`
- Executed: `True`
- HTTP: `302 Found`

### `GET /captcha`

- Show OK: `True`
- Dry-run OK: `True`
- Executed: `True`
- HTTP: `200 OK`

### `GET /competition-levels`

- Show OK: `True`
- Dry-run OK: `True`
- Executed: `True`
- HTTP: `200 OK`

### `GET /competition-levels/{competition_level_id}/icon`

- Show OK: `True`
- Dry-run OK: `True`
- Executed: `True`
- HTTP: `200 OK`

### `GET /competitions`

- Show OK: `True`
- Dry-run OK: `True`
- Executed: `True`
- HTTP: `200 OK`

### `GET /competitions/{competition_id}`

- Show OK: `True`
- Dry-run OK: `True`
- Executed: `True`
- HTTP: `200 OK`

### `GET /competitions/{competition_id}/agreement`

- Show OK: `True`
- Dry-run OK: `True`
- Executed: `True`
- HTTP: `200 OK`

### `POST /competitions/{competition_id}/agreement`

- Show OK: `True`
- Dry-run OK: `True`
- Executed: `False`
- Reason: mutating method verified as dry-run only without --execute

### `GET /configuration`

- Show OK: `True`
- Dry-run OK: `True`
- Executed: `True`
- HTTP: `200 OK`

### `GET /consultant`

- Show OK: `True`
- Dry-run OK: `True`
- Executed: `True`
- HTTP: `404 Not Found`

### `GET /consultant-datasets`

- Show OK: `True`
- Dry-run OK: `True`
- Executed: `True`
- HTTP: `404 Not Found`

### `GET /consultant-information/consultant-dos-and-donts`

- Show OK: `True`
- Dry-run OK: `True`
- Executed: `True`
- HTTP: `404 Not Found`

### `GET /consultant-information/consultant-faqs`

- Show OK: `True`
- Dry-run OK: `True`
- Executed: `True`
- HTTP: `404 Not Found`

### `GET /consultant-information/osmosis-allocation-guide-consultants`

- Show OK: `True`
- Dry-run OK: `True`
- Executed: `True`
- HTTP: `404 Not Found`

### `GET /consultant-information/visualization-tool`

- Show OK: `True`
- Dry-run OK: `True`
- Executed: `True`
- HTTP: `404 Not Found`

### `GET /consultant-program`

- Show OK: `True`
- Dry-run OK: `True`
- Executed: `True`
- HTTP: `404 Not Found`

### `GET /consultant-program/{language}`

- Show OK: `True`
- Dry-run OK: `True`
- Executed: `True`
- HTTP: `404 Not Found`

### `GET /consultant/boards`

- Show OK: `True`
- Dry-run OK: `True`
- Executed: `True`
- HTTP: `404 Not Found`

### `GET /consultant/boards/leader`

- Show OK: `True`
- Dry-run OK: `True`
- Executed: `True`
- HTTP: `200 OK`

### `GET /consultant/summary`

- Show OK: `True`
- Dry-run OK: `True`
- Executed: `True`
- HTTP: `404 Not Found`

### `GET /data-categories`

- Show OK: `True`
- Dry-run OK: `True`
- Executed: `True`
- HTTP: `200 OK`

### `GET /data-fields`

- Show OK: `True`
- Dry-run OK: `True`
- Executed: `True`
- HTTP: `200 OK`

### `GET /data-fields/summary`

- Show OK: `True`
- Dry-run OK: `True`
- Executed: `True`
- HTTP: `200 OK`

### `GET /data-fields/{field_id}`

- Show OK: `True`
- Dry-run OK: `True`
- Executed: `True`
- HTTP: `200 OK`

### `GET /data-sets`

- Show OK: `True`
- Dry-run OK: `True`
- Executed: `True`
- HTTP: `200 OK`

### `GET /data-sets/search`

- Show OK: `True`
- Dry-run OK: `True`
- Executed: `True`
- HTTP: `400 Bad Request`

### `POST /data-sets/search`

- Show OK: `True`
- Dry-run OK: `True`
- Executed: `False`
- Reason: mutating method verified as dry-run only without --execute

### `GET /data-sets/{dataset_id}`

- Show OK: `True`
- Dry-run OK: `True`
- Executed: `True`
- HTTP: `200 OK`

### `POST /errors/api/2/envelope`

- Show OK: `True`
- Dry-run OK: `True`
- Executed: `False`
- Reason: mutating method verified as dry-run only without --execute

### `GET /events`

- Show OK: `True`
- Dry-run OK: `True`
- Executed: `True`
- HTTP: `200 OK`

### `OPTIONS /events`

- Show OK: `True`
- Dry-run OK: `True`
- Executed: `True`
- HTTP: `200 OK`

### `GET /events/{event_id}`

- Show OK: `True`
- Dry-run OK: `True`
- Executed: `True`
- HTTP: `200 OK`

### `GET /messages`

- Show OK: `True`
- Dry-run OK: `True`
- Executed: `True`
- HTTP: `404 Not Found`

### `GET /operators`

- Show OK: `True`
- Dry-run OK: `True`
- Executed: `True`
- HTTP: `200 OK`

### `GET /search`

- Show OK: `True`
- Dry-run OK: `True`
- Executed: `True`
- HTTP: `400 Bad Request`

### `GET /simulations`

- Show OK: `True`
- Dry-run OK: `True`
- Executed: `True`
- HTTP: `405 Method Not Allowed`

### `OPTIONS /simulations`

- Show OK: `True`
- Dry-run OK: `True`
- Executed: `True`
- HTTP: `200 OK`

### `POST /simulations`

- Show OK: `True`
- Dry-run OK: `True`
- Executed: `False`
- Reason: mutating method verified as dry-run only without --execute

### `GET /simulations/super-selection`

- Show OK: `True`
- Dry-run OK: `True`
- Executed: `True`
- HTTP: `200 OK`

### `POST /simulations/super-selection`

- Show OK: `True`
- Dry-run OK: `True`
- Executed: `False`
- Reason: mutating method verified as dry-run only without --execute

### `GET /simulations/{simulation_id}`

- Show OK: `True`
- Dry-run OK: `True`
- Executed: `True`
- HTTP: `200 OK`

### `GET /suggest/examples`

- Show OK: `True`
- Dry-run OK: `True`
- Executed: `True`
- HTTP: `200 OK`

### `POST /suggest/examples`

- Show OK: `True`
- Dry-run OK: `True`
- Executed: `False`
- Reason: mutating method verified as dry-run only without --execute

### `GET /suggest/expression`

- Show OK: `True`
- Dry-run OK: `True`
- Executed: `True`
- HTTP: `404 Not Found`

### `POST /suggest/expression`

- Show OK: `True`
- Dry-run OK: `True`
- Executed: `False`
- Reason: mutating method verified as dry-run only without --execute

### `GET /suggest/fastexpr`

- Show OK: `True`
- Dry-run OK: `True`
- Executed: `True`
- HTTP: `404 Not Found`

### `POST /suggest/fastexpr`

- Show OK: `True`
- Dry-run OK: `True`
- Executed: `False`
- Reason: mutating method verified as dry-run only without --execute

### `GET /suggest/fields`

- Show OK: `True`
- Dry-run OK: `True`
- Executed: `True`
- HTTP: `200 OK`

### `POST /suggest/fields`

- Show OK: `True`
- Dry-run OK: `True`
- Executed: `False`
- Reason: mutating method verified as dry-run only without --execute

### `GET /tags`

- Show OK: `True`
- Dry-run OK: `True`
- Executed: `True`
- HTTP: `200 OK`

### `GET /teams`

- Show OK: `True`
- Dry-run OK: `True`
- Executed: `True`
- HTTP: `405 Method Not Allowed`

### `GET /tutorial-pages`

- Show OK: `True`
- Dry-run OK: `True`
- Executed: `True`
- HTTP: `404 Not Found`

### `GET /tutorial-pages/{page_id}`

- Show OK: `True`
- Dry-run OK: `True`
- Executed: `True`
- HTTP: `404 Not Found`

### `GET /tutorial/{tutorial_slug}`

- Show OK: `True`
- Dry-run OK: `True`
- Executed: `True`
- HTTP: `200 OK`

### `GET /tutorials`

- Show OK: `True`
- Dry-run OK: `True`
- Executed: `True`
- HTTP: `200 OK`

### `GET /user/email/change`

- Show OK: `True`
- Dry-run OK: `True`
- Executed: `True`
- HTTP: `405 Method Not Allowed`

### `POST /user/email/change`

- Show OK: `True`
- Dry-run OK: `True`
- Executed: `False`
- Reason: mutating method verified as dry-run only without --execute

### `GET /user/email/reverify`

- Show OK: `True`
- Dry-run OK: `True`
- Executed: `True`
- HTTP: `405 Method Not Allowed`

### `POST /user/email/reverify`

- Show OK: `True`
- Dry-run OK: `True`
- Executed: `False`
- Reason: mutating method verified as dry-run only without --execute

### `GET /user/email/verify`

- Show OK: `True`
- Dry-run OK: `True`
- Executed: `True`
- HTTP: `405 Method Not Allowed`

### `POST /user/email/verify`

- Show OK: `True`
- Dry-run OK: `True`
- Executed: `False`
- Reason: mutating method verified as dry-run only without --execute

### `GET /user/password/change`

- Show OK: `True`
- Dry-run OK: `True`
- Executed: `True`
- HTTP: `405 Method Not Allowed`

### `POST /user/password/change`

- Show OK: `True`
- Dry-run OK: `True`
- Executed: `False`
- Reason: mutating method verified as dry-run only without --execute

### `GET /user/password/forgot`

- Show OK: `True`
- Dry-run OK: `True`
- Executed: `True`
- HTTP: `405 Method Not Allowed`

### `POST /user/password/forgot`

- Show OK: `True`
- Dry-run OK: `True`
- Executed: `False`
- Reason: mutating method verified as dry-run only without --execute

### `GET /user/password/reset`

- Show OK: `True`
- Dry-run OK: `True`
- Executed: `True`
- HTTP: `405 Method Not Allowed`

### `POST /user/password/reset`

- Show OK: `True`
- Dry-run OK: `True`
- Executed: `False`
- Reason: mutating method verified as dry-run only without --execute

### `GET /user/token`

- Show OK: `True`
- Dry-run OK: `True`
- Executed: `True`
- HTTP: `405 Method Not Allowed`

### `POST /user/token`

- Show OK: `True`
- Dry-run OK: `True`
- Executed: `False`
- Reason: mutating method verified as dry-run only without --execute

### `GET /users`

- Show OK: `True`
- Dry-run OK: `True`
- Executed: `True`
- HTTP: `405 Method Not Allowed`

### `GET /users/self`

- Show OK: `True`
- Dry-run OK: `True`
- Executed: `True`
- HTTP: `200 OK`

### `GET /users/self/achievements`

- Show OK: `True`
- Dry-run OK: `True`
- Executed: `True`
- HTTP: `200 OK`

### `GET /users/self/activities/pyramid-alphas`

- Show OK: `True`
- Dry-run OK: `True`
- Executed: `True`
- HTTP: `200 OK`

### `GET /users/self/activities/pyramid-multipliers`

- Show OK: `True`
- Dry-run OK: `True`
- Executed: `True`
- HTTP: `200 OK`

### `GET /users/self/activities/simulations`

- Show OK: `True`
- Dry-run OK: `True`
- Executed: `True`
- HTTP: `200 OK`

### `GET /users/self/agreements`

- Show OK: `True`
- Dry-run OK: `True`
- Executed: `True`
- HTTP: `200 OK`

### `GET /users/self/alphas`

- Show OK: `True`
- Dry-run OK: `True`
- Executed: `True`
- HTTP: `200 OK`

### `GET /users/self/alphas/summary`

- Show OK: `True`
- Dry-run OK: `True`
- Executed: `True`
- HTTP: `200 OK`

### `GET /users/self/consultant/summary`

- Show OK: `True`
- Dry-run OK: `True`
- Executed: `True`
- HTTP: `200 OK`

### `GET /users/self/consultant/tutorial/summary`

- Show OK: `True`
- Dry-run OK: `True`
- Executed: `True`
- HTTP: `200 OK`

### `PATCH /users/self/consultant/tutorial/summary`

- Show OK: `True`
- Dry-run OK: `True`
- Executed: `False`
- Reason: mutating method verified as dry-run only without --execute

### `GET /users/self/messages`

- Show OK: `True`
- Dry-run OK: `True`
- Executed: `True`
- HTTP: `200 OK`

### `GET /users/self/messages/summary`

- Show OK: `True`
- Dry-run OK: `True`
- Executed: `True`
- HTTP: `200 OK`

### `GET /users/self/pyramid/alphas`

- Show OK: `True`
- Dry-run OK: `True`
- Executed: `True`
- HTTP: `404 Not Found`

### `GET /users/self/teams`

- Show OK: `True`
- Dry-run OK: `True`
- Executed: `True`
- HTTP: `200 OK`

### `GET /users/self/tutorial/steps`

- Show OK: `True`
- Dry-run OK: `True`
- Executed: `True`
- HTTP: `200 OK`

### `GET /users/self/tutorial/summary`

- Show OK: `True`
- Dry-run OK: `True`
- Executed: `True`
- HTTP: `200 OK`

### `GET /users/{user_id}`

- Show OK: `True`
- Dry-run OK: `True`
- Executed: `True`
- HTTP: `200 OK`

### `GET /users/{user_id}/achievements`

- Show OK: `True`
- Dry-run OK: `True`
- Executed: `True`
- HTTP: `200 OK`

### `GET /users/{user_id}/activities`

- Show OK: `True`
- Dry-run OK: `True`
- Executed: `True`
- HTTP: `200 OK`

### `GET /users/{user_id}/activities/diversity`

- Show OK: `True`
- Dry-run OK: `True`
- Executed: `True`
- HTTP: `200 OK`

### `OPTIONS /users/{user_id}/alphas`

- Show OK: `True`
- Dry-run OK: `True`
- Executed: `True`
- HTTP: `200 OK`

### `GET /users/{user_id}/competitions`

- Show OK: `True`
- Dry-run OK: `True`
- Executed: `True`
- HTTP: `200 OK`

### `GET /users/{user_id}/settings/simulation`

- Show OK: `True`
- Dry-run OK: `True`
- Executed: `True`
- HTTP: `200 OK`

### `GET /video-courses`

- Show OK: `True`
- Dry-run OK: `True`
- Executed: `True`
- HTTP: `200 OK`
