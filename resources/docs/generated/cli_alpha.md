# WQB Alpha CLI

`wqb alpha` 封装 alpha 相关 endpoint。

已覆盖：`all`、`list`、`get`、`patch`、`submit`、`check`、`distribution`、`lists`、`super-selection`、`unsubmitted`、`walkthrough`、`related`、`recordsets`、`recordset`、`pnl`、`sharpe`、`yearly-stats`、`performance-comparison`、`correlation base|self|prod|power-pool`。

等待策略：`check`、`recordsets`、`recordset`、`pnl`、`sharpe`、`yearly-stats`、`correlation`、`performance-comparison` 以及可能返回 `Retry-After` 的 alpha 读取命令默认等待最终结果，默认 `--max-wait-seconds 900`。

安全策略：`PATCH` 和 `submit` 会直接发送请求。

完整 endpoint 到命令映射见 `api_inventory/BUSINESS_CLI_COVERAGE.md`。
