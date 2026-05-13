# J_并行回测

## Role
- 批量提交 `I` 的表达式候选并获取真实 alpha 结果入口。
- 负责把 simulation parent / child 展开到真实 `alpha_id`。

## Upstream
- `I_表达式候选集`

## Downstream
- `K_结果诊断`

## Inputs
### Necessary
- `I` 的 `simulation_batch__...json`
- 当前主塔三元组
- 并行策略：
  - 非 `GLB`：`10(m) * 8(c)`
  - `GLB`：`5(m) * 4(c)`

### Optional
- 只选主批次而非全批次的策略
- visualization 设置

## Outputs
### Necessary
- `08_J_parallel_simulation/primary_batch__{REGION}_D{DELAY}_{CATEGORY}.json`
- `08_J_parallel_simulation/primary_batch_payload__{REGION}_D{DELAY}_{CATEGORY}.json`
- `08_J_parallel_simulation/concurrent_simulate__{REGION}_D{DELAY}_{CATEGORY}.json`
- `08_J_parallel_simulation/alpha_candidates__{REGION}_D{DELAY}_{CATEGORY}.json`
- `08_J_parallel_simulation/node_summary.md`

### Optional
- parent simulation url
- child simulation id 列表
- candidate_id 到 alpha_id 的映射过程日志

## Success Criteria
- 成功提交整批回测。
- 成功把结果展开到真实 `alpha_id`。

## Failure Criteria
- 只拿到 parent，没有拿到真实 alpha 结果。
- 并行策略未按当前 tower 类型执行。
