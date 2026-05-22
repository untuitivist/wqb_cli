# K 结果诊断

## 目标

判断 J 的 alpha 是否达到提交标准，并决定下一跳。K 不允许让 agent loop 停止，除非下一跳是 L/M。

## 输入

必要：

- J 的 `alpha_results.json`。
- I 的 `expression_candidates.json`。
- H 的 `mechanism_hypotheses.json`。
- F 的 `candidate_datafields.json`。

可选：

- 历史 K 节点。
- visualization 结果和 recordsets。

## 只允许的 CLI

```powershell
wqb alpha get <alpha_id> --output <node_dir>/alpha__alpha_id.json
wqb alpha check <alpha_id> --max-wait-seconds 900 --output <node_dir>/alpha_check__alpha_id.json
wqb alpha pnl <alpha_id> --output <node_dir>/pnl__alpha_id.json
wqb alpha yearly-stats <alpha_id> --output <node_dir>/yearly_stats__alpha_id.json
wqb alpha correlation self <alpha_id> --max-wait-seconds 900 --output <node_dir>/self_corr__alpha_id.json
wqb alpha correlation prod <alpha_id> --max-wait-seconds 900 --output <node_dir>/prod_corr__alpha_id.json
```

## 输出

必要：

- `diagnosis.md`
- `next_node.json`：只能是 `D`、`F`、`H`、`I`、`L`、`BEST_K_BRANCH`。
- `best_alpha_candidates.json`
- `node_summary.md`

可选：

- `best_k_decision.md`
- `visualization_notes.md`

## 诊断标准

- sharpe > 1.58。
- fitness > 1。
- 1% < turnover < 70%。
- margin > 0.1%。
- visualization 支持结果时优先级更高。
- 与历史 K 对比，选择最有希望的机制/字段/表达式分支。

## 下一跳规则

- 指标通过且 check 风险可控：到 L。
- 字段层弱、OS 弱、字段选择错误：回 F。
- 机制解释弱或经济学假设需重排：回 H。
- 机制对但表达式结构弱：回 I。
- 主塔选择错误或点塔收益不足：回 D。
- 历史 best K 明显更优：触发 BEST_K_BRANCH，将 bestK 后续节点收入 `bestK/error_branch/`，然后从 H 继续。

## 成功条件

- 明确下一跳并写入 `next_node.json`。
- 到 M 前不停止 agent loop。
## 硬规则：线性混信号候选直接判失败

- K 诊断时，如果候选依赖多个独立经济机制线性加权，即使指标过线也不能进入 L/M。
- 如果候选只是围绕单一主字段/单一主机制做非线性变换、时间平滑、幂次、分段或门控，不应按“混信号”判失败。
- 发现混信号时，`next_node.json` 必须指向 `H` 或 `D`，原因写 `mixed_signal_forbidden`。
- 目标塔和主要收益来源不一致时，不能因为 `MATCHES_PYRAMID` 通过就提交。
- 可提交 alpha 必须同时满足硬指标、相关性/ladder 检查，以及单一经济机制约束。
