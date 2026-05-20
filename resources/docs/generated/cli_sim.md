# WQB Simulation CLI

`wqb sim` 封装 simulation 接口。

已覆盖：`list`、`options`、`get`、`create`、`super-selection`。

安全策略：`create` 和 `super-selection --method POST` 默认 dry-run，必须 `--execute` 才会执行。

完整 endpoint 到命令映射见 `api_inventory/BUSINESS_CLI_COVERAGE.md`。
