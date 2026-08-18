# M 提交与记录

## 目标

对 L 完整通过的本 run Alpha 执行或记录最终提交动作。simulate 与 submit 语义严格分离：J 只发起 simulation，只有 M 可以调用 `wqb alpha submit` 将 Alpha 入库。

## 输入

- A 的 `run_manifest.json` 与明确提交授权
- B 的累计提交目标和停止条件
- C 的提交额度快照
- L 的 `submission_candidates.json` 与完整终检证据

## 推荐命令

```cmd
wqb alpha get <alpha_id> --output <node_dir>\alpha_before_submit__<alpha_id>.json
wqb alpha patch <alpha_id> --input <node_dir>\alpha_patch__<alpha_id>.json --output <node_dir>\patch_result__<alpha_id>.json
wqb alpha submit <alpha_id> --output <node_dir>\submit_result__<alpha_id>.json
wqb alpha get <alpha_id> --output <node_dir>\alpha_after_submit__<alpha_id>.json
```

`patch` 仅在预注册的描述、tag 或说明确实需要时执行，不是提交前强制步骤。

## 提交规则

- `alpha_submission_allowed` 不是 `true`、额度不足或候选不在 L 清单时，禁止调用 submit，并记录 no-op 原因。
- 提交前重新读取 Alpha 状态与当日额度，已提交的 Alpha 只登记为幂等成功，不重复提交。
- 每个 Alpha 最多发出一次结果确定的 submit 请求。响应不确定时先通过只读 `alpha get` 核对；无法确认则标记 inconclusive，禁止盲目重复 mutating request。
- 只有 `wqb alpha submit` 返回 `ok = true` 且 `submit_code = 200`，并且该命令内置的最终 Alpha GET/`alpha_after_submit` 证明平台已提交，才能计入成功数量。
- 多个候选按 L 的跨 cluster 顺序提交；达到本轮剩余额度或累计目标后立即停止新的 submit。
- M 只能处理当前 batch workflow 产生的 Alpha，不得接收其他流程的 candidate、alpha 或检查文件。

## 输出

- `submission_plan.md`
- `submit_results.json`
- `submission_ledger.json`：记录 alpha id、cluster、请求时间、确认状态及累计目标进度。
- `next_action.json`：只能是 `OBJECTIVE_REACHED`、`NEW_BATCH` 或 `WAIT_FOR_QUOTA`。
- `alpha_before_submit__*.json`
- `patch_result__*.json`（可选）
- `submit_result__*.json`
- `alpha_after_submit__*.json`
- `commands.md`
- `node_summary.md`

## 成功条件

- 每个提交候选都有明确的提交、已提交、额度阻止、失败或 inconclusive 结果。
- 成功数由平台提交后状态复核，不由 HTTP 请求次数推断。
- 累计目标未完成时，本流程不得把候选转给其他流程：有额度则创建新的独立 batch run，从 A 开始；无额度则等待下一平台提交日并重新核验。

## 下一跳

- 累计目标完成：结束。
- 累计目标未完成且有额度：创建新的独立 batch run，从本流程 A 开始。
- 额度不足：等待额度恢复后在本节点重新核验。
