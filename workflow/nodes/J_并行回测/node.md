# J 并行回测

## 目标

使用 `wqb sim create` 对 I 的表达式批次做真实回测，并记录 alpha_id 与完整结果。

## 输入

必要：
- I 的 `expression_candidates.json`
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
- `alpha_results.json`: real alpha_id, metrics, check, and visualization status
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

## 成功条件

- Every successful simulation records a real `alpha_id`.
- Do not use a child simulation id as a substitute for alpha_id.
- Prefer results with visualization available; downrank results without visualization in K.

## 下一路

- `K 结果诊断`
# Runtime lifecycle invariants

- J simulates exactly one `READY` idea per invocation and may route to itself while other ideas remain.
- Simulation records stay linked to candidate records. After a restart, reusable child simulation IDs are queried again and only missing or failed candidates are submitted anew. If a parent was already created, its ledger remains bound to that parent and recovery performs `sim get`; a 401/403 routes the run to `NEEDS_AUTH` without replaying `sim create`.
- A platform failure marks only the current idea as `ERROR`; ready ideas continue immediately, then failed ideas retry after bounded cooldown.
- Idea states progress through `READY`, `SIMULATING`, and `COMPLETED`. User abort requests stop further work for that idea after the active provider call exits.
- K receives the cumulative alpha results from every completed idea in the latest locked plan, not results from earlier plan versions.
