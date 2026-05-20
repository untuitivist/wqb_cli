# WQB Alpha CLI

`wqb alpha` 封装 alpha 相关 endpoint。

已覆盖：`all`、`list`、`get`、`patch`、`submit`、`check`、`distribution`、`lists`、`super-selection`、`unsubmitted`、`walkthrough`、`related`、`recordsets`、`recordset`、`pnl`、`sharpe`、`yearly-stats`、`performance-comparison`、`correlation base|self|prod|power-pool`。

安全策略：`PATCH` 和 `submit` 默认 dry-run，必须 `--execute` 才会执行。

完整 endpoint 到命令映射见 `api_inventory/BUSINESS_CLI_COVERAGE.md`。
