# WQB CLI API 使用文档

- Generated at: `2026-05-18T17:45:12.523838+00:00`
- Endpoint count: `109`
- 所有 endpoint 都支持 `api show` 和 `api call`。
- `GET/HEAD/OPTIONS/POST/PATCH/PUT/DELETE` 都会直接发送请求。
- 参数既可命令行传入，也可用 `--input request.json` 传入。

## 全局命令

```powershell
python -m wqb_cli api stats
python -m wqb_cli api list
python -m wqb_cli api list --prefix /alphas
python -m wqb_cli auth status
```

## JSON 输入格式

```json
{
  "path_vars": {
    "alpha_id": "..."
  },
  "params": {
    "limit": "1"
  },
  "json": {}
}
```

## Endpoint CLI 文档索引

- `/achievements` -> `cli_docs/achievements/usage.md`
- `/achievements/{achievement_id}/icon` -> `cli_docs/achievements/achievement_id/icon/usage.md`
- `/agreements` -> `cli_docs/agreements/usage.md`
- `/alphas` -> `cli_docs/alphas/usage.md`
- `/alphas/distribution` -> `cli_docs/alphas/distribution/usage.md`
- `/alphas/lists` -> `cli_docs/alphas/lists/usage.md`
- `/alphas/sample-alpha-id-walkthrough` -> `cli_docs/alphas/sample-alpha-id-walkthrough/usage.md`
- `/alphas/super-selection` -> `cli_docs/alphas/super-selection/usage.md`
- `/alphas/unsubmitted` -> `cli_docs/alphas/unsubmitted/usage.md`
- `/alphas/{alpha_id}` -> `cli_docs/alphas/alpha_id/usage.md`
- `/alphas/{alpha_id}/alphas` -> `cli_docs/alphas/alpha_id/alphas/usage.md`
- `/alphas/{alpha_id}/check` -> `cli_docs/alphas/alpha_id/check/usage.md`
- `/alphas/{alpha_id}/correlations` -> `cli_docs/alphas/alpha_id/correlations/usage.md`
- `/alphas/{alpha_id}/correlations/power-pool` -> `cli_docs/alphas/alpha_id/correlations/power-pool/usage.md`
- `/alphas/{alpha_id}/correlations/prod` -> `cli_docs/alphas/alpha_id/correlations/prod/usage.md`
- `/alphas/{alpha_id}/correlations/self` -> `cli_docs/alphas/alpha_id/correlations/self/usage.md`
- `/alphas/{alpha_id}/performance-comparison` -> `cli_docs/alphas/alpha_id/performance-comparison/usage.md`
- `/alphas/{alpha_id}/recordsets` -> `cli_docs/alphas/alpha_id/recordsets/usage.md`
- `/alphas/{alpha_id}/recordsets/pnl` -> `cli_docs/alphas/alpha_id/recordsets/pnl/usage.md`
- `/alphas/{alpha_id}/recordsets/sharpe` -> `cli_docs/alphas/alpha_id/recordsets/sharpe/usage.md`
- `/alphas/{alpha_id}/recordsets/yearly-stats` -> `cli_docs/alphas/alpha_id/recordsets/yearly-stats/usage.md`
- `/alphas/{alpha_id}/recordsets/{record_set_name}` -> `cli_docs/alphas/alpha_id/recordsets/record_set_name/usage.md`
- `/alphas/{alpha_id}/submit` -> `cli_docs/alphas/alpha_id/submit/usage.md`
- `/authentication` -> `cli_docs/authentication/usage.md`
- `/authentication/brainlabs` -> `cli_docs/authentication/brainlabs/usage.md`
- `/authentication/persona` -> `cli_docs/authentication/persona/usage.md`
- `/authentication/support` -> `cli_docs/authentication/support/usage.md`
- `/authentication/workday` -> `cli_docs/authentication/workday/usage.md`
- `/captcha` -> `cli_docs/captcha/usage.md`
- `/competition-levels` -> `cli_docs/competition-levels/usage.md`
- `/competition-levels/{competition_level_id}/icon` -> `cli_docs/competition-levels/competition_level_id/icon/usage.md`
- `/competitions` -> `cli_docs/competitions/usage.md`
- `/competitions/{competition_id}` -> `cli_docs/competitions/competition_id/usage.md`
- `/competitions/{competition_id}/boards/{board_type}` -> `cli_docs/competitions/competition_id/boards/board_type/usage.md`
- `/competitions/{competition_id}/agreement` -> `cli_docs/competitions/competition_id/agreement/usage.md`
- `/competitions/spc/submissions` -> `cli_docs/competitions/spc/submissions/usage.md`
- `/competitions/spc/submissions/{submission_id}` -> `cli_docs/competitions/spc/submissions/submission_id/usage.md`
- `/configuration` -> `cli_docs/configuration/usage.md`
- `/consultant` -> `cli_docs/consultant/usage.md`
- `/consultant-datasets` -> `cli_docs/consultant-datasets/usage.md`
- `/consultant-information/consultant-dos-and-donts` -> `cli_docs/consultant-information/consultant-dos-and-donts/usage.md`
- `/consultant-information/consultant-faqs` -> `cli_docs/consultant-information/consultant-faqs/usage.md`
- `/consultant-information/osmosis-allocation-guide-consultants` -> `cli_docs/consultant-information/osmosis-allocation-guide-consultants/usage.md`
- `/consultant-information/visualization-tool` -> `cli_docs/consultant-information/visualization-tool/usage.md`
- `/consultant-program` -> `cli_docs/consultant-program/usage.md`
- `/consultant-program/{language}` -> `cli_docs/consultant-program/language/usage.md`
- `/consultant/boards` -> `cli_docs/consultant/boards/usage.md`
- `/consultant/boards/leader` -> `cli_docs/consultant/boards/leader/usage.md`
- `/consultant/boards/spc` -> `cli_docs/consultant/boards/spc/usage.md`
- `/consultant/boards/{board_type}` -> `cli_docs/consultant/boards/board_type/usage.md`
- `/consultant/summary` -> `cli_docs/consultant/summary/usage.md`
- `/data-categories` -> `cli_docs/data-categories/usage.md`
- `/data-fields` -> `cli_docs/data-fields/usage.md`
- `/data-fields/summary` -> `cli_docs/data-fields/summary/usage.md`
- `/data-fields/{field_id}` -> `cli_docs/data-fields/field_id/usage.md`
- `/data-sets` -> `cli_docs/data-sets/usage.md`
- `/data-sets/search` -> `cli_docs/data-sets/search/usage.md`
- `/data-sets/{dataset_id}` -> `cli_docs/data-sets/dataset_id/usage.md`
- `/errors/api/2/envelope` -> `cli_docs/errors/api/2/envelope/usage.md`
- `/events` -> `cli_docs/events/usage.md`
- `/events/{event_id}` -> `cli_docs/events/event_id/usage.md`
- `/messages` -> `cli_docs/messages/usage.md`
- `/operators` -> `cli_docs/operators/usage.md`
- `/search` -> `cli_docs/search/usage.md`
- `/simulations` -> `cli_docs/simulations/usage.md`
- `/simulations/super-selection` -> `cli_docs/simulations/super-selection/usage.md`
- `/simulations/{simulation_id}` -> `cli_docs/simulations/simulation_id/usage.md`
- `/suggest/examples` -> `cli_docs/suggest/examples/usage.md`
- `/suggest/expression` -> `cli_docs/suggest/expression/usage.md`
- `/suggest/fastexpr` -> `cli_docs/suggest/fastexpr/usage.md`
- `/suggest/fields` -> `cli_docs/suggest/fields/usage.md`
- `/tags` -> `cli_docs/tags/usage.md`
- `/teams` -> `cli_docs/teams/usage.md`
- `/tutorial-pages` -> `cli_docs/tutorial-pages/usage.md`
- `/tutorial-pages/{page_id}` -> `cli_docs/tutorial-pages/page_id/usage.md`
- `/tutorial/{tutorial_slug}` -> `cli_docs/tutorial/tutorial_slug/usage.md`
- `/tutorials` -> `cli_docs/tutorials/usage.md`
- `/user/email/change` -> `cli_docs/user/email/change/usage.md`
- `/user/email/reverify` -> `cli_docs/user/email/reverify/usage.md`
- `/user/email/verify` -> `cli_docs/user/email/verify/usage.md`
- `/user/password/change` -> `cli_docs/user/password/change/usage.md`
- `/user/password/forgot` -> `cli_docs/user/password/forgot/usage.md`
- `/user/password/reset` -> `cli_docs/user/password/reset/usage.md`
- `/user/token` -> `cli_docs/user/token/usage.md`
- `/users` -> `cli_docs/users/usage.md`
- `/users/self` -> `cli_docs/users/self/usage.md`
- `/users/self/achievements` -> `cli_docs/users/self/achievements/usage.md`
- `/users/self/activities/pyramid-alphas` -> `cli_docs/users/self/activities/pyramid-alphas/usage.md`
- `/users/self/activities/pyramid-multipliers` -> `cli_docs/users/self/activities/pyramid-multipliers/usage.md`
- `/users/self/activities/simulations` -> `cli_docs/users/self/activities/simulations/usage.md`
- `/users/self/agreements` -> `cli_docs/users/self/agreements/usage.md`
- `/users/self/alphas` -> `cli_docs/users/self/alphas/usage.md`
- `/users/self/alphas/summary` -> `cli_docs/users/self/alphas/summary/usage.md`
- `/users/self/consultant/summary` -> `cli_docs/users/self/consultant/summary/usage.md`
- `/users/self/consultant/tutorial/summary` -> `cli_docs/users/self/consultant/tutorial/summary/usage.md`
- `/users/self/messages` -> `cli_docs/users/self/messages/usage.md`
- `/users/self/messages/summary` -> `cli_docs/users/self/messages/summary/usage.md`
- `/users/self/pyramid/alphas` -> `cli_docs/users/self/pyramid/alphas/usage.md`
- `/users/self/teams` -> `cli_docs/users/self/teams/usage.md`
- `/users/self/tutorial/steps` -> `cli_docs/users/self/tutorial/steps/usage.md`
- `/users/self/tutorial/summary` -> `cli_docs/users/self/tutorial/summary/usage.md`
- `/users/{user_id}` -> `cli_docs/users/user_id/usage.md`
- `/users/{user_id}/achievements` -> `cli_docs/users/user_id/achievements/usage.md`
- `/users/{user_id}/activities` -> `cli_docs/users/user_id/activities/usage.md`
- `/users/{user_id}/activities/diversity` -> `cli_docs/users/user_id/activities/diversity/usage.md`
- `/users/{user_id}/alphas` -> `cli_docs/users/user_id/alphas/usage.md`
- `/users/{user_id}/competitions` -> `cli_docs/users/user_id/competitions/usage.md`
- `/users/{user_id}/settings/simulation` -> `cli_docs/users/user_id/settings/simulation/usage.md`
- `/video-courses` -> `cli_docs/video-courses/usage.md`
