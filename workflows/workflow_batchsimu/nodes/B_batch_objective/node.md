# B 批量研究目标

## 目标

把本轮问题定义为可比较的模板族筛选实验，预先声明成功指标、预算、停止条件和不可回答的问题。

B 研究的是 family density 和结构多样性，不以“找到一条最高 Sharpe alpha”为目标。

## 输入

- A 的 `run_manifest.json`
- 研究方给出的目标类别、region 或预算约束；未给出时必须在本节点内形成有证据的选择范围。

## 必须定义

- primary question：哪些经济上不同的模板族在固定环境下具有更高有效密度。
- region policy：排除 `CHN` 和 `USA`。`CHN` 的当前 Sharpe 门槛高于 `2.07`；`USA` 研究拥挤、同类参与者多，均不作为本流程的新研究目标。
- experimental unit：一个带完整 settings 和 lineage 的 candidate experiment。
- primary metrics：execution-ready rate、quality density、check-pass density。
- diversity metric：基于 READY candidate 的 IS-PnL correlation cluster。
- error budget、simulation budget 和最大扩展轮数。
- 不把非终态结果、诊断 run 或不同 settings cell 混入统计。

## 输出

- `batch_objective.json`
- `family_screen_contract.json`
- `quality_gates.json`
- `stop_conditions.json`
- `assumptions.md`
- `commands.md`
- `node_summary.md`

`quality_gates.json` 必须明确 Regular 或 Super 的 Sharpe、fitness、turnover、margin、check 口径；不得等结果出来后再移动门槛。

## 成功条件

- primary metric、denominator、最小有效样本、预算和停止条件全部在回测前固定。
- `batch_objective.json` 明确记录 `excluded_regions = ["CHN", "USA"]`，且候选 region 不在排除集合内。
- 明确哪些结论只能视为探索性证据。
- `alpha_submission_allowed` 仍为 `false`。

## 下一跳

- `C 目标与设置冻结`
