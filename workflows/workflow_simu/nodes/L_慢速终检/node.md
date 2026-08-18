# L 慢速终检

## 目标

对 K 选出的少量候选做提交前慢速终检，包括完整 check、年度稳定性、self/prod correlation、pool 价值和提交风险。L 仍只处理本 run 内的真实 alpha。

## 输入

必要：

- K 的 `best_alpha_candidates.json`。
- K 的 `candidate_diagnoses.json`。
- J 的 `simulation_results.json`。

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
wqb alpha pnl <alpha_id> --output <node_dir>/pnl__alpha_id.json
wqb alpha yearly-stats <alpha_id> --output <node_dir>/yearly_stats__alpha_id.json
```

## 输出

必要：

- `final_check.md`
- `final_candidate_audit.json`
- `submission_candidates.json`
- `next_node.json`：只能是 `M`、`F`、`G`、`H` 或 `I`。
- `node_summary.md`

可选：

- `alpha_check__*.json`
- `self_corr__*.json`
- `prod_corr__*.json`
- `performance_comparison__*.json`
- `pnl__*.json`
- `yearly_stats__*.json`

## 决策规则

- 所有慢速响应必须属于 J 记录的真实 `alpha_id`，不得用 simulation id 或 child id 代替。
- 任一最终 check 为 FAIL，不得进入 M。
- self/prod correlation、年度退化或 pool 边际价值不足时，按根因回到 I/H/F；不得在 L 改 expression。
- API 暂时失败只能标为 inconclusive，不得伪造通过，也不得盲目重发不确定的 mutating request。
- `submission_candidates.json` 可以为空；为空时必须通过 `next_node.json` 回退，不能结束本轮。

## 成功条件

- 通过慢速终检则到 M。
- 未通过则明确根因并回到 F/G/H/I 之一。

## 下一跳

- `M 提交与记录`
- `F 数据与字段可行性`
- `G 证据包与结构约束`
- `H 可检验机制契约`
- `I 小规模表达式候选`
