# J 并行回测

## 目标

使用 `wqb sim create/get` 对 I 的表达式批次做真实回测，并记录 alpha_id 与完整结果。

## 输入

必要：

- I 的 `expression_candidates.json`。
- D 的 `main_tower.json`。

可选：

- E 的 `super_constraints.json`。

## 只允许的 CLI

```powershell
wqb sim options --output <node_dir>/sim_options.json
wqb sim create --input <node_dir>/simulation_batch.json --execute --output <node_dir>/simulation_create.json
wqb sim get <simulation_id> --max-wait-seconds 900 --output <node_dir>/simulation_get.json
wqb alpha get <alpha_id> --output <node_dir>/alpha__alpha_id.json
wqb alpha check <alpha_id> --output <node_dir>/alpha_check__alpha_id.json
wqb alpha recordsets <alpha_id> --output <node_dir>/recordsets__alpha_id.json
```

## 输出

必要：

- `simulation_batch.json`
- `simulation_create.json`
- `simulation_get.json`
- `alpha_results.json`：真实 alpha_id、指标、check、visualization 状态。
- `node_summary.md`

可选：

- `alpha__*.json`
- `alpha_check__*.json`
- `recordsets__*.json`

## 并发规则

- REGULAR FASTEXPR multi：非 GLB 建议每批 10 条；GLB 建议每批 5 条。
- REGULAR 同时运行槽位：非 GLB 最多 8；GLB 最多 4。
- SUPER 同时运行槽位最多 3。
- REGULAR PYTHON 不能 multi。
- simulation 等待最多 15 分钟；当前 `wqb sim get` 只暴露 `--max-wait-seconds`，如果需要 `Retry-After` 乘以 10，应先补 CLI，而不是在 workflow 自建脚本。
- 无原因 `FAIL/ERROR` 记录为平台通用失败，不当作表达式经济学失败。

## 成功条件

- 每个成功 simulation 都记录真实 `alpha_id`。
- 不以 child simulation id 替代 alpha_id。
- 尽量开启 visualization；无 visualization 的结果在 K 中降权。

## 下一跳

- `K 结果诊断`
