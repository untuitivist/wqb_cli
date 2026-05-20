# simulations create

提交一个 simulation 请求。

命令：

```powershell
wqb sim create --input <input.json> --execute --output <output.json>
```

`--execute` 是必需的，因为这是会创建平台资源的写操作。

成功判断：

- `response.status_code = 201`
- `response.location` 包含 `/simulations/<simulation_id>`
- `response.retry_after` 可能包含初始等待建议

并行与批量约束：

- `REGULAR_FASTEXPR_MULTI` 单请求最多 10 条；建议非 `GLB` 用 10，`GLB` 用 5。
- `REGULAR_PYTHON` 不能 multi，只能单条请求。
- `SUPER` 按单条 SUPER 请求跑，外部并发最多 3。
- `REGULAR` 外部并发：非 `GLB` 最多 8，`GLB` 最多 4。

真实流程示例：

- `examples/backtest_modes.md`：覆盖 REGULAR FASTEXPR 单跑、REGULAR FASTEXPR multi-simu、REGULAR PYTHON 单跑、SUPER 单跑四类回测。
