# J 同步回测

## 目标

使用 `wqb sim create` 对 I 的有界候选批次做真实回测。agent 等待本轮返回并保存每个候选的真实 `alpha_id`、执行状态和完整结果。

本节点不使用后台 worker，不打开 SQLite simulation store，也不承担模板族大批量筛选。

## 输入

必要：
- I 的 `expression_candidates.json`
- I 的 `simulation_batch.json`
- I 的 `iteration_plan.json`
- D 的 `main_tower.json`

可选：
- E 的 `super_constraints.json`

## 推荐使用的 CLI

```powershell
wqb sim options --output <node_dir>/sim_options.json
wqb sim create --input <node_dir>/simulation_batch.json --max-wait-seconds 900 --output <node_dir>/simulation_create.json
wqb sim get <child_simulation_id> --max-wait-seconds 900 --output <node_dir>/child_simulation_get.json
wqb alpha get <alpha_id> --output <node_dir>/alpha__alpha_id.json
wqb alpha check <alpha_id> --max-wait-seconds 900 --output <node_dir>/alpha_check__alpha_id.json
wqb alpha recordsets <alpha_id> --max-wait-seconds 900 --output <node_dir>/recordsets__alpha_id.json
```

`wqb sim create` now waits for the parent simulation result by default. `201 Created` is only `201 Created, waiting for results...`; do not treat it as final backtest success.

For multi-simulation, `wqb sim create` also waits for child simulations and places them under top-level `children`. Use `wqb sim get <child_simulation_id>` only when re-checking a child later.

## 输出

必要：
- `simulation_batch.json`
- `simulation_create.json`
- `simulation_results.json`: candidate、child simulation、真实 alpha_id 和执行状态的映射
- `alpha_results.json`: metrics、check、PnL/visualization availability
- `failure_events.json`
- `node_summary.md`

可选：
- `child_simulation_get.json`
- `alpha__*.json`
- `alpha_check__*.json`
- `recordsets__*.json`

## 并发规则

- REGULAR FASTEXPR multi: use 10 expressions per non-GLB batch, 5 per GLB batch.
- REGULAR external concurrency: max 8 outside GLB, max 4 for GLB.
- SUPER external concurrency: max 3.
- REGULAR PYTHON cannot use multi-simulation.
- Simulation wait cap defaults to 900 seconds.
- Unexplained `FAIL/ERROR` should be recorded as platform execution failure first, not immediately as expression economics failure.
- 不得超过 I 声明的候选上限，也不得在 J 临时生成替代表达式
- `204 / 401 / 429` 由 CoreClient 自动续期/重放；最终仍异常时记录为可恢复平台事件
- POST 结果不确定时不得盲目重发，以免创建重复 alpha

## 成功条件

- Every successful simulation records a real `alpha_id`.
- Do not use a child simulation id as a substitute for alpha_id.
- Prefer results with visualization available; downrank results without visualization in K.
- 每个 I candidate 都有且只有一个明确 J 状态；执行失败也必须保留 lineage

## 下一路

- `K 个体结果诊断`
