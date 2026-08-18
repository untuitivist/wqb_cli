# L 慢速终检

## 目标

对 K 从不同真实 IS-PnL cluster 选出的少量候选执行提交前慢速终检。检查标准与平台的单因子终检一致，但输入、命令产物和控制流全部保留在当前 batch run 内。

L 不修改 expression、manifest、K 排名或 J 的 SQLite，也不提交 Alpha。

## 输入

- A 的 run manifest 与提交授权
- B 的 quality gates、提交目标和 stop conditions
- C 的提交额度快照
- J/K 记录的本 run 真实 alpha id、完整结果和 `best_alpha_candidates.json`

## 推荐命令

```cmd
wqb alpha get <alpha_id> --output <node_dir>\alpha__<alpha_id>.json
wqb alpha check <alpha_id> --max-wait-seconds 900 --output <node_dir>\alpha_check__<alpha_id>.json
wqb alpha correlation self <alpha_id> --max-wait-seconds 900 --output <node_dir>\self_corr__<alpha_id>.json
wqb alpha correlation prod <alpha_id> --max-wait-seconds 900 --output <node_dir>\prod_corr__<alpha_id>.json
wqb alpha performance-comparison <alpha_id> --max-wait-seconds 900 --output <node_dir>\performance_comparison__<alpha_id>.json
wqb alpha pnl <alpha_id> --output <node_dir>\pnl__<alpha_id>.json
wqb alpha yearly-stats <alpha_id> --output <node_dir>\yearly_stats__<alpha_id>.json
```

## 决策规则

- 所有响应必须属于 K 记录的本 run 真实 `alpha_id`，不得用 simulation id、child id 或其他 run 的 alpha 代替。
- 任一必需 check 为 `FAIL` 或 `ERROR` 不得进入 M；`PENDING` 必须等到确定结果或标记 inconclusive。
- self/prod correlation、年度退化、pool 边际价值或平台完整 check 不满足预注册门槛时不得进入 M。
- API 暂时失败只能标为 inconclusive；不得伪造通过，也不得盲目重发结果不确定的 mutating request。
- 慢速终检只缩小候选集合，不得在 L 改 expression、settings 或用新的 Alpha 替换失败候选。
- `submission_candidates.json` 可以为空；为空且累计目标未完成时，`next_action.json` 必须创建新的独立 batch run 并从 A 开始，不能跳到其他流程。

## 输出

- `final_check.md`
- `final_candidate_audit.json`
- `submission_candidates.json`
- `next_action.json`：只能是 `M_SUBMIT`、`NEW_BATCH` 或 `STOP_OBJECTIVE_REACHED`；最后一种只允许在进入 L 期间平台账本已证明累计目标完成时使用。
- `alpha__*.json`
- `alpha_check__*.json`
- `self_corr__*.json`
- `prod_corr__*.json`
- `performance_comparison__*.json`
- `pnl__*.json`
- `yearly_stats__*.json`
- `commands.md`
- `node_summary.md`

## 成功条件

- 每个输入候选都有确定的通过、失败或 inconclusive 结论和原始证据。
- 只有全部慢速终检通过的候选进入 `submission_candidates.json`。
- 所有候选均失败时仍给出同一流程内可执行的下一 batch 方向，当前 J 数据库保持只读历史记录。

## 下一跳

- `M 提交与记录`
- 创建新的独立 batch run，从本流程 A 开始
- 仅在平台确认累计提交目标已经完成时结束
