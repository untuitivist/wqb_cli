# K 个体结果诊断

## 目标

逐条诊断 J 的候选，区分执行失败、表达式失败、字段或单位失败、机制失败和经济表现失败，再决定本流程内的下一跳。

K 不能用均值掩盖单个候选，也不计算模板族密度。未进入 L 时必须立即回退到 F/G/H/I 之一。

## 输入

必要：
- J 的 `alpha_results.json`
- J 的 `simulation_results.json`
- J 的 `failure_events.json`
- I 的 `expression_candidates.json`
- I 的 `iteration_plan.json`
- H 的 `mechanism_contracts.json`
- H 的 `mechanism_hypotheses.json`
- F 的 `candidate_datafields.json`

可选：
- 历史 K 节点
- visualization 结果
- alpha recordsets

## 推荐 CLI

```powershell
wqb alpha get <alpha_id> --output <node_dir>/alpha__<alpha_id>.json
wqb alpha check <alpha_id> --max-wait-seconds 900 --output <node_dir>/alpha_check__<alpha_id>.json
wqb alpha pnl <alpha_id> --output <node_dir>/pnl__<alpha_id>.json
wqb alpha yearly-stats <alpha_id> --output <node_dir>/yearly_stats__<alpha_id>.json
wqb alpha correlation self <alpha_id> --max-wait-seconds 900 --output <node_dir>/self_corr__<alpha_id>.json
wqb alpha correlation prod <alpha_id> --max-wait-seconds 900 --output <node_dir>/prod_corr__<alpha_id>.json
```

## 输出

必要：
- `diagnosis.md`
- `candidate_diagnoses.json`
- `failure_classification.json`
- `quality_gate_results.json`
- `pnl_diagnostics.json`
- `next_node.json`
- `best_alpha_candidates.json`
- `node_summary.md`

可选：
- `visualization_notes.md`
- `best_k_decision.md`

## 诊断顺序

1. 验证 candidate、simulation、child simulation 和真实 `alpha_id` 的一一映射。
2. 先按 `platform/authentication`、`syntax/operator`、`data/unit`、`mechanism`、`economic_metrics`、`checks` 分类失败。
3. 只对有真实 alpha 结果的候选计算指标、年度稳定性、PnL 形态和相关性。
4. 对照 H 的 falsification conditions 判断机制是否被否定；不能用一次平台失败否定机制。
5. 选择进入 L 的少量候选，或按根因回退。

## Regular 质量门槛

- `sharpe > 1.58`
- `fitness > 1`
- `1% < turnover < 70%`
- `margin > 0.1%`
- "checks"下的元素里的"result"没有FAIL状态

Super 候选必须使用 E 的 `super_constraints.json`，不得套用 Regular 门槛。

## 硬要求：必须回退

如果本节点没有决定进入 `L`，则必须回退，而且：

- `K` 必须自行判断回退节点
- 不允许停下来问用户回退到哪里
- 回退节点只能从 `[F, G, H, I]` 中选
- 不允许回退到 `D`
- 不允许停留在 `K`
- `next_node.json` 只能是 `F`、`G`、`H`、`I` 或 `L`

## 回退判断规则

- 回 `F`
  - 字段层面太弱
  - OS 表现差
  - 当前字段整体没有继续优化价值
  - prod/self/coverage 等表现说明应换字段

- 回 `G`
  - 当前资料不足
  - 本地社区、官方文档、平台资料、论文研报证据不够
  - 需要补模板、补论文、补经验再判断

- 回 `H`
  - 字段本身未必错，但经济学解释不成立或太弱
  - 机制方向需要重构
  - 同一字段应换另一套机制理解

- 回 `I`
  - 机制对，但表达式结构弱
  - 参数、非线性、时间平滑、关系量仍可优化

认证、限流或平台执行异常只能标记为 inconclusive，不得写成字段或机制失败。POST 结果不确定时不得重新提交同一 payload。

## 混信号规则

- 若候选依赖多个独立经济机制的线性加权，即使指标过线也不能进入 `L`
- 若候选仅围绕单字段或单机制做非线性、时间平滑、门控或关系量，不按混信号判死
- 发现混信号时，优先回 `H` 或 `I`

## 成功条件

- 明确下一跳并写入 `next_node.json`
- 每个 I candidate 都有唯一诊断记录和可追溯根因
- 进入 L 的候选全部记录真实 `alpha_id` 并满足本类型质量门槛
- 到 `M` 前不停止 agent loop

## 下一跳

- `L 慢速终检`
- 或回退到 `F/G/H/I`
