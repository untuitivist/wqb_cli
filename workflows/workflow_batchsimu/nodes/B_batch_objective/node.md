# B 批量研究目标

## 目标

把本轮问题定义为可比较的模板族筛选实验，预先声明成功指标、预算、停止条件和不可回答的问题。

B 研究的是 family density 和结构多样性，不以“找到一条最高 Sharpe alpha”为目标；如果 A 已授权提交，还要预注册如何从不同 IS-PnL cluster 选择少量终检候选。

## 输入

- A 的 `run_manifest.json`
- 研究方给出的目标类别、region 或预算约束；未给出时必须在本节点内形成有证据的选择范围。

## 必须定义

- primary question：哪些经济上不同的模板族在固定环境下具有更高有效密度。
- region preference：建议降低 `CHN` 和 `USA` 的优先级。依据是 `CHN` 当前 Sharpe 门槛高于 `2.07`，而 `USA` 研究拥挤、同类参与者多；这是研究建议，不是禁止规则。
- experimental unit：一个带完整 settings 和 lineage 的 candidate experiment。
- primary metrics：execution-ready rate、quality density、check-pass density。
- diversity metric：基于 READY candidate 的 IS-PnL correlation cluster。
- 单 run 的 error budget 与 simulation budget；它们只限制本 run，不得在累计提交目标未完成时变成 campaign 停止条件。
- 提交目标、单 run 最大终检候选数、跨 cluster 去重规则，以及目标未完成时继续新 batch 的条件。
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
- `batch_objective.json` 记录 `deprioritized_regions = ["CHN", "USA"]` 和 `region_preference_advisory = true`；若仍选择其中之一，必须记录本轮证据和取舍理由。
- 明确哪些结论只能视为探索性证据。
- `alpha_submission_allowed` 与 A 一致，B 不得扩大授权；允许提交时，`stop_conditions.json` 必须区分“本 run 结束”和“累计提交目标完成”。
- 已授权的 campaign 只有平台确认累计提交目标完成或用户显式取消时才停止；模板质量弱、候选为空、额度暂时不足或单 run 预算耗尽都只触发 `NEW_BATCH`/`WAIT_FOR_QUOTA`。

## 下一跳

- `C 目标与设置冻结`
