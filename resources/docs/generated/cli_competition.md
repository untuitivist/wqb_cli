# WQB Competition CLI

`wqb competition` 封装 competition 接口。

已覆盖：

- `wqb competition list`
- `wqb competition get <competition_id>`
- `wqb competition agreement <competition_id> --method GET|POST`

安全策略：agreement 的 `POST` 会直接发送请求。

完整 endpoint 到命令映射见 `api_inventory/BUSINESS_CLI_COVERAGE.md`。
