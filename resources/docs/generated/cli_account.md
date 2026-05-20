# WQB Account CLI

`wqb account` 封装账号相关 endpoint。

已覆盖命令:

- `wqb account email-change --method GET|POST`
- `wqb account email-reverify --method GET|POST`
- `wqb account email-verify --method GET|POST`
- `wqb account password-change --method GET|POST`
- `wqb account password-forgot --method GET|POST`
- `wqb account password-reset --method GET|POST`
- `wqb account token --method GET|POST`

安全策略:

- `POST` 默认只 dry-run。
- 必须显式 `--execute` 才会执行账号变更类请求。

验证记录:

- 所有 `GET` 与 `POST` 命令已完成 dry-run。
- `GET` 实际调用已执行，当前平台真实状态主要为 `405 Method Not Allowed` 或 `401 Unauthorized`。
