# WQB User CLI

`wqb user` 封装 user/self/user-id 相关接口。

已覆盖：`list`、`self`、`messages`、`messages-summary`、`consultant-summary`、`consultant-tutorial-summary`、`consultant-tutorial-patch`、`achievements`、`simulation-activity`、`pyramid-alphas`、`pyramid-multipliers`、`agreements`、`alphas-summary`、`pyramid-alpha-summary`、`teams`、`tutorial-steps`、`tutorial-summary`、`get`、`user-achievements`、`user-activities`、`user-diversity`、`user-alphas-options`、`user-competitions`、`user-simulation-settings`。

安全策略：`consultant-tutorial-patch` 会直接发送请求。

完整 endpoint 到命令映射见 `api_inventory/BUSINESS_CLI_COVERAGE.md`。
