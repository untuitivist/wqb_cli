# API inventory

Updated 2026-09-21T16:08:26.074426+00:00. 127 registered paths.

Method lists include server-advertised operations; inspect live_probe for actual verification. Private option choices are excluded.

| Path | Methods | Latest OPTIONS |
| --- | --- | --- |
| `/achievements` | GET, HEAD | 405 |
| `/achievements/{achievement_id}/icon` | GET | SKIPPED_NO_OBSERVED_ID |
| `/agreements` | GET, HEAD, OPTIONS, POST | 200 |
| `/agreements/privacy-policy` | DELETE, GET, HEAD, OPTIONS, PATCH, PUT | 200 |
| `/agreements/referral-agreement` | DELETE, GET, HEAD, OPTIONS, PATCH, PUT | 200 |
| `/alphas` | GET, OPTIONS, PATCH, POST, PUT | 200 |
| `/alphas/distribution` | GET, HEAD, OPTIONS, PATCH, PUT | 200 |
| `/alphas/lists` | GET, HEAD, OPTIONS, PATCH, PUT | 200 |
| `/alphas/sample-alpha-id-walkthrough` | GET, HEAD, OPTIONS, PATCH, PUT | 200 |
| `/alphas/super-selection` | GET, HEAD, OPTIONS, PATCH, PUT | 200 |
| `/alphas/unsubmitted` | GET, HEAD, OPTIONS, PATCH, PUT | 200 |
| `/alphas/{alpha_id}` | GET, HEAD, OPTIONS, PATCH, PUT | 200 |
| `/alphas/{alpha_id}/alphas` | GET, HEAD, OPTIONS | 200 |
| `/alphas/{alpha_id}/check` | GET, HEAD, OPTIONS, PATCH, PUT | 200 |
| `/alphas/{alpha_id}/correlations` | GET | 404 |
| `/alphas/{alpha_id}/correlations/power-pool` | GET, HEAD | 405 |
| `/alphas/{alpha_id}/correlations/prod` | GET, HEAD | 405 |
| `/alphas/{alpha_id}/correlations/self` | GET, HEAD | 405 |
| `/alphas/{alpha_id}/performance-comparison` | GET | 404 |
| `/alphas/{alpha_id}/recordsets` | GET, HEAD | 405 |
| `/alphas/{alpha_id}/recordsets/pnl` | GET, HEAD | 405 |
| `/alphas/{alpha_id}/recordsets/sharpe` | GET, HEAD | 405 |
| `/alphas/{alpha_id}/recordsets/turnover` | GET, HEAD | 405 |
| `/alphas/{alpha_id}/recordsets/yearly-stats` | GET, HEAD | 405 |
| `/alphas/{alpha_id}/recordsets/{record_set_name}` | GET, HEAD | 405 |
| `/alphas/{alpha_id}/submit` | GET, HEAD, OPTIONS, PATCH, POST, PUT | 200 |
| `/authentication` | DELETE, GET, HEAD, OPTIONS, POST | 200 |
| `/authentication/brainlabs` | GET, HEAD, OPTIONS, POST | 200 |
| `/authentication/persona` | GET, HEAD, OPTIONS, POST | 200 |
| `/authentication/support` | GET, HEAD, OPTIONS | 200 |
| `/authentication/workday` | GET, HEAD, OPTIONS, POST | 200 |
| `/captcha` | GET, HEAD, OPTIONS, POST | 200 |
| `/competition-levels` | GET, HEAD | 405 |
| `/competition-levels/{competition_level_id}/icon` | GET | SKIPPED_NO_OBSERVED_ID |
| `/competitions` | GET, HEAD, OPTIONS | 200 |
| `/competitions/spc/submissions` | GET, HEAD, OPTIONS, POST | 200 |
| `/competitions/spc/submissions/{submission_id}` | GET, PATCH, PUT | SKIPPED_NO_OBSERVED_ID |
| `/competitions/{competition_id}` | GET | SKIPPED_NO_OBSERVED_ID |
| `/competitions/{competition_id}/agreement` | GET, POST | SKIPPED_NO_OBSERVED_ID |
| `/competitions/{competition_id}/boards/{board_type}` | GET | SKIPPED_NO_OBSERVED_ID |
| `/configuration` | GET, HEAD, OPTIONS | 200 |
| `/consultant` | GET | 404 |
| `/consultant-datasets` | GET | 404 |
| `/consultant-information/consultant-dos-and-donts` | GET | 404 |
| `/consultant-information/consultant-faqs` | GET | 404 |
| `/consultant-information/osmosis-allocation-guide-consultants` | GET | 404 |
| `/consultant-information/visualization-tool` | GET | 404 |
| `/consultant-program` | GET | 404 |
| `/consultant-program/{language}` | GET | 404 |
| `/consultant/boards` | GET | 404 |
| `/consultant/boards/leader` | GET, HEAD, OPTIONS | 200 |
| `/consultant/boards/spc` | GET, HEAD, OPTIONS | 200 |
| `/consultant/boards/{board_type}` | GET, HEAD, OPTIONS | 200 |
| `/consultant/summary` | GET | 404 |
| `/data-categories` | GET, HEAD, OPTIONS | 200 |
| `/data-fields` | GET, HEAD | 400 |
| `/data-fields/summary` | GET, HEAD | 500 |
| `/data-fields/{field_id}` | GET, HEAD | 400 |
| `/data-fields/{field_id}/visualize` | POST | 400 |
| `/data-sets` | GET, HEAD, OPTIONS | 200 |
| `/data-sets/search` | GET, HEAD, POST | 500 |
| `/data-sets/{dataset_id}` | GET, HEAD, OPTIONS | 200 |
| `/errors/api/2/envelope` | POST | 404 |
| `/events` | GET, HEAD, OPTIONS | 200 |
| `/events/{event_id}` | GET | SKIPPED_NO_OBSERVED_ID |
| `/messages` | GET | 404 |
| `/messages/announcements` | GET, HEAD, OPTIONS, PATCH, PUT | 200 |
| `/messages/notifications` | GET, HEAD, OPTIONS, PATCH, PUT | 200 |
| `/operators` | GET, HEAD, OPTIONS | 200 |
| `/search` | GET, HEAD, OPTIONS | 200 |
| `/simulations` | GET, OPTIONS, POST | 200 |
| `/simulations/super-selection` | GET, HEAD, OPTIONS, POST | 200 |
| `/simulations/{simulation_id}` | GET | SKIPPED_NO_OBSERVED_ID |
| `/suggest/examples` | GET, HEAD, OPTIONS, POST | 200 |
| `/suggest/expression` | GET, POST | 404 |
| `/suggest/fastexpr` | GET, POST | 404 |
| `/suggest/fields` | GET, HEAD, OPTIONS, POST | 200 |
| `/tags` | GET, HEAD, OPTIONS, POST | 200 |
| `/teams` | GET, OPTIONS, POST | 200 |
| `/tutorial-pages` | GET, HEAD, OPTIONS | 200 |
| `/tutorial-pages/{page_id}` | GET, HEAD, OPTIONS | 200 |
| `/tutorial/{tutorial_slug}` | GET, HEAD, OPTIONS | 200 |
| `/tutorials` | GET, HEAD, OPTIONS | 200 |
| `/user/email/change` | GET, OPTIONS, POST | 200 |
| `/user/email/reverify` | GET, OPTIONS, POST | 200 |
| `/user/email/verify` | GET, OPTIONS, POST | 200 |
| `/user/password/change` | GET, OPTIONS, POST | 200 |
| `/user/password/forgot` | GET, OPTIONS, POST | 200 |
| `/user/password/reset` | GET, OPTIONS, POST | 200 |
| `/user/token` | GET, POST | 405 |
| `/users` | GET, OPTIONS, POST | 200 |
| `/users/self` | DELETE, GET, HEAD, OPTIONS, PATCH, PUT | 200 |
| `/users/self/achievements` | GET, HEAD | 405 |
| `/users/self/activities/pyramid-alphas` | GET, HEAD | 405 |
| `/users/self/activities/pyramid-multipliers` | GET, HEAD | 405 |
| `/users/self/activities/simulations` | GET, HEAD | 405 |
| `/users/self/activities/submissions` | GET, HEAD | 405 |
| `/users/self/agreements` | GET, HEAD | 500 |
| `/users/self/alphas` | GET, HEAD, OPTIONS | 200 |
| `/users/self/alphas/summary` | GET, HEAD, OPTIONS | 200 |
| `/users/self/alphas/{alpha_id}/before-and-after-performance` | GET, HEAD, OPTIONS | 200 |
| `/users/self/consultant/summary` | GET, HEAD | 405 |
| `/users/self/consultant/tutorial/summary` | GET, HEAD, OPTIONS, PATCH | 200 |
| `/users/self/messages` | GET, HEAD | 405 |
| `/users/self/messages/summary` | GET, HEAD, PATCH | 405 |
| `/users/self/pyramid/alphas` | GET | 404 |
| `/users/self/streak` | GET, HEAD | 405 |
| `/users/self/tags` | GET, HEAD, OPTIONS | 200 |
| `/users/self/teams` | GET, HEAD | 405 |
| `/users/self/tutorial/steps` | GET, HEAD, OPTIONS | 200 |
| `/users/self/tutorial/summary` | GET, HEAD, OPTIONS, PATCH, POST | 200 |
| `/users/{user_id}` | DELETE, GET, HEAD, OPTIONS, PATCH, PUT | 200 |
| `/users/{user_id}/achievements` | GET, HEAD | 405 |
| `/users/{user_id}/activities` | GET, HEAD | 405 |
| `/users/{user_id}/activities/diversity` | GET, HEAD | 405 |
| `/users/{user_id}/activities/{activity_name}` | GET, HEAD | 405 |
| `/users/{user_id}/alphas` | GET, HEAD, OPTIONS | 200 |
| `/users/{user_id}/competitions` | GET, HEAD | 405 |
| `/users/{user_id}/consultant` | GET, HEAD | 405 |
| `/users/{user_id}/consultant/summary` | GET, HEAD | 405 |
| `/users/{user_id}/osmosis/scale-points` | POST | 405 |
| `/users/{user_id}/osmosis/scale-points/ALL` | GET, HEAD | 405 |
| `/users/{user_id}/osmosis/summary` | GET, HEAD | 405 |
| `/users/{user_id}/profile` | GET, HEAD, OPTIONS | 200 |
| `/users/{user_id}/researcher` | GET, HEAD | 405 |
| `/users/{user_id}/settings/simulation` | GET, HEAD, OPTIONS, POST | 200 |
| `/video-courses` | GET, HEAD, OPTIONS | 200 |
