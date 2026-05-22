# WQB Suggest CLI

`wqb suggest` 封装推荐/建议接口。

已覆盖命令:

- `wqb suggest examples --method GET|POST`
- `wqb suggest expression --method GET|POST`
- `wqb suggest fastexpr --method GET|POST`
- `wqb suggest fields --method GET|POST`

安全策略:

- `POST` 会直接发送 prompt/context。

验证记录:

- 所有命令已完成参数检查。
- `GET` 实际调用已执行，当前平台真实状态为 `401 Unauthorized` 或 `404 Not Found`。
