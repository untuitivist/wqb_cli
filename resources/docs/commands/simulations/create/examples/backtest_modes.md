# 回测模式示例

`wqb sim create` 通过同一个 `/simulations` API 覆盖四类常用回测：

- `REGULAR` + `FASTEXPR` 单条 simulation。
- `REGULAR` + `FASTEXPR` multi-simulation。
- `REGULAR` + `PYTHON` 单条 simulation。
- `SUPER` 单条 simulation。

这些示例都是真实 CLI 运行结果。
示例目标是说明请求结构、命令链路、并发约束和平台返回形态，不代表 alpha 可提交。
完整输入 JSON 示例见 `examples/input_json.md`。

## 并行与批量规则

回测时要区分“单个请求里放多少条表达式”和“同时跑多少个 simulation 请求”：

- `REGULAR_FASTEXPR_MULTI`：一个 multi 请求最多 10 条表达式。
- `REGULAR_FASTEXPR_MULTI` 推荐批量大小：非 `GLB` 区域用 10，`GLB` 区域用 5。
- `REGULAR_FASTEXPR_MULTI` 有时会因为表达式太多或表达式复杂度太高报错；遇到这种情况先降低单批条数。
- `REGULAR_PYTHON`：不能 multi，只能一条 simulation 一个请求。
- `SUPER`：不能用 REGULAR multi 方式合批，按单条 SUPER simulation 请求跑。
- 同时进行的 `REGULAR` 回测请求数：`region != "GLB"` 时最多 8 个，`region == "GLB"` 时最多 4 个。
- 同时进行的 `SUPER` 回测请求数：最多 3 个。

推荐调度策略：

```text
if type == SUPER:
    concurrent_requests = 3
    batch_size = 1
elif language == PYTHON:
    concurrent_requests = 8 if region != "GLB" else 4
    batch_size = 1
elif language == FASTEXPR:
    concurrent_requests = 8 if region != "GLB" else 4
    batch_size = 10 if region != "GLB" else 5
```

这里的 `batch_size` 只对 `REGULAR_FASTEXPR_MULTI` 有意义。
`concurrent_requests` 是外部调度器同时启动的 simulation 请求数，不是 `wqb sim create` 命令本身的参数。

## REGULAR FASTEXPR 单条回测

输入文件：

```text
wqb_cli/docs/commands/simulations/create/fixtures/regular_fastexpr_single.json
```

输入 JSON 示例见 `examples/input_json.md#regular-fastexpr-single-simulation`。

创建命令：

```powershell
D:\_soft\Anaconda\envs\WQBRAIN\Scripts\wqb.exe sim create --input "wqb_cli\\docs\\commands\simulations\create\fixtures\regular_fastexpr_single.json" --execute --output "wqb_cli\\docs\\commands\simulations\create\outputs\regular_fastexpr_single_create.json"
```

轮询命令：

```powershell
D:\_soft\Anaconda\envs\WQBRAIN\Scripts\wqb.exe sim get 1sA5Evcma4GlbBexARpKkiX --max-wait-seconds 900 --output "wqb_cli\\docs\\commands\simulations\get\outputs\regular_fastexpr_single_get.json"
```

真实结果摘要：

```json
{
  "simulation_id": "1sA5Evcma4GlbBexARpKkiX",
  "type": "REGULAR",
  "language": "FASTEXPR",
  "status": "WARNING",
  "alpha": "rKbwexz3",
  "warning": "REVERSION_COMPONENT"
}
```

经验点：

- FASTEXPR 单条请求体是一个 JSON object。
- `WARNING` 且带 `alpha` 时，alpha 已生成，可以继续 `alpha get`。

## REGULAR FASTEXPR 批量回测

输入文件：

```text
wqb_cli/docs/commands/simulations/create/fixtures/regular_fastexpr_multi.json
```

输入 JSON 示例见 `examples/input_json.md#regular-fastexpr-multi-simulation`。

创建命令：

```powershell
D:\_soft\Anaconda\envs\WQBRAIN\Scripts\wqb.exe sim create --input "wqb_cli\\docs\\commands\simulations\create\fixtures\regular_fastexpr_multi.json" --execute --output "wqb_cli\\docs\\commands\simulations\create\outputs\regular_fastexpr_multi_create.json"
```

父任务轮询命令：

```powershell
D:\_soft\Anaconda\envs\WQBRAIN\Scripts\wqb.exe sim get 9Xb69y251KaGqyWKGddux --max-wait-seconds 900 --output "wqb_cli\\docs\\commands\simulations\get\outputs\regular_fastexpr_multi_get.json"
```

父任务结果摘要：

```json
{
  "simulation_id": "9Xb69y251KaGqyWKGddux",
  "status": "COMPLETE",
  "children": [
    "2gwGaU59a5dqcySQM4Ft1gn",
    "3RTDPvcRM4JtczS18UmrIqML"
  ]
}
```

子任务轮询命令：

```powershell
D:\_soft\Anaconda\envs\WQBRAIN\Scripts\wqb.exe sim get 2gwGaU59a5dqcySQM4Ft1gn --max-wait-seconds 900 --output "wqb_cli\\docs\\commands\simulations\get\outputs\regular_fastexpr_multi_child_1_get.json"
D:\_soft\Anaconda\envs\WQBRAIN\Scripts\wqb.exe sim get 3RTDPvcRM4JtczS18UmrIqML --max-wait-seconds 900 --output "wqb_cli\\docs\\commands\simulations\get\outputs\regular_fastexpr_multi_child_2_get.json"
```

子任务结果摘要：

```json
[
  {
    "simulation_id": "2gwGaU59a5dqcySQM4Ft1gn",
    "parent": "9Xb69y251KaGqyWKGddux",
    "status": "WARNING",
    "alpha": "rKbwexz3"
  },
  {
    "simulation_id": "3RTDPvcRM4JtczS18UmrIqML",
    "parent": "9Xb69y251KaGqyWKGddux",
    "status": "WARNING",
    "alpha": "58L1gX66"
  }
]
```

经验点：

- multi-simulation 的输入文件是 JSON array，长度 2 到 10。
- 同一个 multi 请求里的 simulation 必须保持这些 settings 一致：`delay`、`region`、`instrumentType`、`language`。
- 父任务只给 `children`，重要结果在 child simulation 里。
- 如果 FASTEXPR multi 报表达式过多或平台通用错误，先从 10 降到 5，再降到单条。

## REGULAR PYTHON 单条回测

输入文件：

```text
wqb_cli/docs/commands/simulations/create/fixtures/regular_python_single.json
```

输入 JSON 示例见 `examples/input_json.md#regular-python-single-simulation`。

创建命令：

```powershell
D:\_soft\Anaconda\envs\WQBRAIN\Scripts\wqb.exe sim create --input "wqb_cli\\docs\\commands\simulations\create\fixtures\regular_python_single.json" --execute --output "wqb_cli\\docs\\commands\simulations\create\outputs\regular_python_single_create.json"
```

轮询命令：

```powershell
D:\_soft\Anaconda\envs\WQBRAIN\Scripts\wqb.exe sim get 2iKEQ32Xm4QFcHqoGYebfM --max-wait-seconds 900 --output "wqb_cli\\docs\\commands\simulations\get\outputs\regular_python_single_get.json"
```

真实结果摘要：

```json
{
  "simulation_id": "2iKEQ32Xm4QFcHqoGYebfM",
  "type": "REGULAR",
  "language": "PYTHON",
  "status": "COMPLETE",
  "alpha": "e7nPQPpl"
}
```

经验点：

- PYTHON 请求体仍然是 `type: REGULAR`，区别在 `settings.language = PYTHON`。
- `regular` 字段里放完整 Python alpha code。
- PYTHON 不能 multi；多个 PYTHON alpha 只能由外部调度器按并发槽位分别提交。
- PYTHON 版更容易因为平台运行环境返回通用 `ERROR`，真实调试时要优先区分“代码定位错误”和“平台通用错误”。

## SUPER 单条回测

输入文件：

```text
wqb_cli/docs/commands/simulations/create/fixtures/super_single.json
```

输入 JSON 示例见 `examples/input_json.md#super-single-simulation`。

创建命令：

```powershell
D:\_soft\Anaconda\envs\WQBRAIN\Scripts\wqb.exe sim create --input "wqb_cli\\docs\\commands\simulations\create\fixtures\super_single.json" --execute --output "wqb_cli\\docs\\commands\simulations\create\outputs\super_single_create.json"
```

轮询命令：

```powershell
D:\_soft\Anaconda\envs\WQBRAIN\Scripts\wqb.exe sim get 41NcougeE57e8Ay3rfZderr --max-wait-seconds 900 --output "wqb_cli\\docs\\commands\simulations\get\outputs\super_single_get.json"
```

真实结果摘要：

```json
{
  "simulation_id": "41NcougeE57e8Ay3rfZderr",
  "type": "SUPER",
  "status": "COMPLETE",
  "alpha": "pwnkdErb",
  "selection": "own == 1",
  "combo": "1"
}
```

经验点：

- SUPER 请求体用 `selection` 和 `combo`，不用 `regular`。
- `selectionHandling` 和 `selectionLimit` 是 SUPER settings 的必需字段。
- selection 布尔条件里 `true` 会被当作未知变量；真实可用写法是 `own == 1`。
- `combo: "alpha"` 会被平台认为是一组表达式；最小可运行组合写法可以用常量权重 `combo: "1"`。
- SUPER 外部并发最多 3 个。

## 取 Alpha 详情

每类 simulation 生成 alpha 后，都可以继续调用 `alpha get`：

```powershell
D:\_soft\Anaconda\envs\WQBRAIN\Scripts\wqb.exe alpha get rKbwexz3 --output "wqb_cli\\docs\\commands\alpha\get\outputs\regular_fastexpr_single_alpha.json"
D:\_soft\Anaconda\envs\WQBRAIN\Scripts\wqb.exe alpha get 58L1gX66 --output "wqb_cli\\docs\\commands\alpha\get\outputs\regular_fastexpr_multi_child_2_alpha.json"
D:\_soft\Anaconda\envs\WQBRAIN\Scripts\wqb.exe alpha get e7nPQPpl --output "wqb_cli\\docs\\commands\alpha\get\outputs\regular_python_single_alpha.json"
D:\_soft\Anaconda\envs\WQBRAIN\Scripts\wqb.exe alpha get pwnkdErb --output "wqb_cli\\docs\\commands\alpha\get\outputs\super_single_alpha.json"
```

这些 alpha 详情文件用于验证 alpha id、语言、状态和指标字段，不作为可提交性判断。
