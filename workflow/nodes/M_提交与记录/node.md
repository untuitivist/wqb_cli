# M 提交与记录

## 目标

执行或记录最终提交动作。达到 M 后本轮 agent loop 才允许停止。

## 输入

必要：

- L 的 `submission_candidates.json`。
- C 的提交额度记录。

可选：

- 需要 patch 的 alpha 描述、tag、说明。

## 推荐使用的 CLI

```powershell
wqb alpha patch <alpha_id> --input <node_dir>/alpha_patch__alpha_id.json --output <node_dir>/patch_result__alpha_id.json
wqb alpha submit <alpha_id> --output <node_dir>/submit_result__alpha_id.json
wqb alpha get <alpha_id> --output <node_dir>/alpha_after_submit__alpha_id.json
```

## 输出

必要：

- `submission_plan.md`
- `submit_results.json`
- `node_summary.md`

可选：

- `patch_result__*.json`
- `submit_result__*.json`
- `alpha_after_submit__*.json`

## 成功条件

- 每个提交候选都有明确的执行结果或明确失败原因。
- 如果额度不足或用户配置为不执行提交，也必须记录 no-op 原因。

## 下一跳

- 本轮结束。
