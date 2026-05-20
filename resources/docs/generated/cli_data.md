# WQB Data CLI

`wqb data` 封装 data categories、datasets、fields 和 operators。

已覆盖：`categories`、`datasets`、`dataset`、`dataset-search`、`fields`、`fields-summary`、`field`、`operators`。

安全策略：`dataset-search --method POST` 默认 dry-run，必须 `--execute` 才会执行。

完整 endpoint 到命令映射见 `api_inventory/BUSINESS_CLI_COVERAGE.md`。
