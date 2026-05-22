# WQB Errors CLI

`wqb errors` 封装错误上报 endpoint。

已覆盖命令:

- `wqb errors envelope --input api_inventory/examples/error_envelope.json`

Raw API:

```text
POST /errors/api/2/envelope
```

安全策略:

- `POST` 会直接发送错误上报。

验证记录:

- 参数检查已通过。
