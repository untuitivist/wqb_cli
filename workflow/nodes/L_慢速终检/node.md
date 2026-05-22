# L 慢速终检

## 目标

对 K 选出的候选 alpha 做提交前慢速检查，包括 check、相关性、pool 价值和提交动作风险。

## 输入

必要：

- K 的 `best_alpha_candidates.json`。

可选：

- C 的提交额度。
- B 的等级 gap。

## 推荐使用的 CLI

```powershell
wqb alpha get <alpha_id> --output <node_dir>/alpha__alpha_id.json
wqb alpha check <alpha_id> --max-wait-seconds 900 --output <node_dir>/alpha_check__alpha_id.json
wqb alpha correlation self <alpha_id> --max-wait-seconds 900 --output <node_dir>/self_corr__alpha_id.json
wqb alpha correlation prod <alpha_id> --max-wait-seconds 900 --output <node_dir>/prod_corr__alpha_id.json
wqb alpha performance-comparison <alpha_id> --max-wait-seconds 900 --output <node_dir>/performance_comparison__alpha_id.json
```

## 输出

必要：

- `final_check.md`
- `submission_candidates.json`
- `next_node.json`：只能是 `M` 或 `K`。
- `node_summary.md`

可选：

- `alpha_check__*.json`
- `self_corr__*.json`
- `prod_corr__*.json`
- `performance_comparison__*.json`

## 成功条件

- 通过慢速终检则到 M。
- 未通过则回 K，并明确失败原因。

## 下一跳

- `M 提交与记录`
- `K 结果诊断`
