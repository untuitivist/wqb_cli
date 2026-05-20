# WQB Suggest CLI

`wqb suggest` 封装推荐/建议接口。

已覆盖命令:

- `wqb suggest examples --method GET|POST`
- `wqb suggest expression --method GET|POST`
- `wqb suggest fastexpr --method GET|POST`
- `wqb suggest fields --method GET|POST`

安全策略:

- `POST` 默认只 dry-run。
- 必须显式 `--execute` 才会实际发送 prompt/context。

验证记录:

- 所有命令已完成 dry-run。
- `GET` 实际调用已执行，当前平台真实状态为 `401 Unauthorized` 或 `404 Not Found`。
