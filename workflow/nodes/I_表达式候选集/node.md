# I 表达式候选集

## 目标

把 H 的机制假设转成可回测表达式批次，并严格遵守 operator 约束。

## 输入

必要：

- H 的 `mechanism_hypotheses.json`。
- F 的 `candidate_datafields.json`。
- D 的 `main_tower.json`。

可选：

- K 回退的表达式弱点。

## 只允许的 CLI

```powershell
wqb data operators --output <node_dir>/operators.json
wqb data fields --output <node_dir>/platform_fields.json
wqb docs show simulations/create/README.md --output <node_dir>/simulation_create_doc.md
```

## 输出

必要：

- `expression_candidates.json`：表达式、settings、字段来源、机制来源。
- `operator_constraints_check.md`
- `node_summary.md`

可选：

- `operators.json`
- `simulation_create_doc.md`

## operator 硬约束

- `ts_quantile(x, d, driver='gaussian')`：字符串参数必须用单引号。
- `kth_element(x, d, k=?)`
- `ts_theilsen(x, y, d)`
- `ts_weighted_decay(x, k=0.5)`：`k` 不可省略。
- `hump_decay(x, p=0)`：`p` 不可省略。
- `group_mean(x, weight, group)`：`weight` 不可省略，可填 `1`。
- `ts_target_tvr_decay(x, lambda_min=0, lambda_max=1, target_tvr=0.1)`
- `ts_target_tvr_hump(x, lambda_min=0, lambda_max=1, target_tvr=0.1)`
- `ts_poly_regression(y, x, d, k=1)`：`k` 不可省略。

## 成功条件

- 形成可直接传给 J 的候选表达式。
- 每条表达式都有机制来源和字段来源。

## 下一跳

- `J 并行回测`
## 硬规则：禁止线性混信号表达式

- 禁止生成 `a * signal1 + b * signal2 + c * signal3` 这类线性加权混信号表达式，尤其是跨机制混合。
- 明确禁止类似 `0.532 * stable + 0.208 * revision + 0.136 * reversal + 0.104 * liquidity + 0.020 * volatility` 的构造。
- 候选表达式必须保持单一主机制；如需处理风险，只能使用非收益型控制，例如过滤、截尾、中性化、衰减或同一字段内部变换。
- 每条候选必须标注 `single_mechanism=true`，并写明主机制字段、目标塔 category、为什么不属于混信号。
- 如果为了过指标必须引入另一个独立 alpha 来源，该候选应作废并回 H/D。
