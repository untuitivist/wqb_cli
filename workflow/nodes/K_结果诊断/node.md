# K 结果诊断

## 目标

判断 J 的 alpha 是否达到提交标准，并决定下一跳。

K 不能让 agent loop 停止，除非下一跳是 `L` 或 `M`。

## 输入

必要：
- J 的 `alpha_results.json`
- I 的 `expression_candidates.json`
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
- `next_node.json`
- `best_alpha_candidates.json`
- `node_summary.md`

可选：
- `visualization_notes.md`
- `best_k_decision.md`

## 诊断标准

- `sharpe > 1.58`
- `fitness > 1`
- `1% < turnover < 70%`
- `margin > 0.1%`
- visualization 支持度更高者优先

## 硬要求：必须回退

如果本节点没有决定进入 `L/M`，则必须回退，而且：

- `K` 必须自行判断回退节点
- 不允许停下来问用户回退到哪里
- 回退节点只能从 `[F, G, H, I]` 中选
- 不能回退到 `D`
- 不能留在 `K`

## 回退判断规则

- 回 `F`
  - 字段层弱
  - 字段 OS 差
  - 字段过度拥挤
  - 当前字段整体没有继续优化价值
- 回 `G`
  - 当前机制资料不足
  - 社区模板、官方文档、平台资料、论文/研报证据不够
  - 需要补资料再判断方向
- 回 `H`
  - 字段本身未必错，但经济学解释弱
  - 机制方向需要重排
  - 同一字段应换另一套机制理解
- 回 `I`
  - 机制对，但表达式结构弱
  - 参数、非线性、时间平滑、门控仍可调整

## 混信号规则

- 若候选依赖多个独立经济机制的线性加权，即使指标过线也不能进 `L/M`
- 若候选仅围绕单字段/单机制做非线性、时间平滑、门控，不按混信号判死
- 发现混信号时，优先回 `H` 或 `I`

## 成功条件

- 明确下一跳并写入 `next_node.json`
- 到 `M` 前不停止 agent loop

## 下一跳

- `L 慢速终检`
- 或回退到 `F/G/H/I`
