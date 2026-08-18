# I 小规模表达式候选

## 目标

I 把 H 的机制契约翻译成一个有明确上限的小规模候选集，并检查 expression、operator、字段单位和 simulation payload。

I 不重新做字段筛选，不重新做机制搜索，不把 H 和 F 的工作混进来。

## 输入

必要：
- H 的 `field_meanings.json`
- H 的 `mechanism_hypotheses.json`
- H 的 `field_unit_contracts.json`
- H 的 `mechanism_contracts.json`
- F 的 `candidate_datafields.json`
- D 的 `main_tower.json`

可选：
- K 的 `diagnosis.md`

## 前提

进入 I 之前，必须已经满足：

- 字段已由 F 选出
- 字段意义已由 H 说明
- 社区、文档、平台、论文证据已由 G 提供并由 H 吸收

如果这些前提不满足，I 应回退 `H` 或 `F`，而不是自己补做。

## 推荐的 CLI

```powershell
wqb data operators --output <node_dir>/operators.json
wqb docs show simulations/create/README.md --output <node_dir>/simulation_create_doc.md
wqb data field <field_id> --output <node_dir>/field_meta__<field_id>.json
```

说明：
- I 可以重新读取字段 meta 做校验
- I 不应把社区或 arXiv 搜索当成主任务；如果发现 H 证据不足，应回退 H

## 输出

必要：
- `iteration_plan.json`
- `expression_candidates.json`
- `simulation_batch.json`
- `operator_constraints_check.md`
- `validation_report.json`
- `node_summary.md`

可选：
- `operators.json`
- `simulation_create_doc.md`
- `field_meta__*.json`

## 表达式构建规则

- `iteration_plan.json` 必须声明本轮问题、候选上限和停止条件；默认上限为 50
- 每条候选必须绑定到单一主机制：`single_mechanism=true`
- 禁止线性混合多个独立收益信号
- OperatorCount < = 5, FieldCount < = 2
- 允许单一机制下的：
  - 同字段时间平滑
  - 同字段非线性变换
  - 同字段关系量
  - 同机制内部的多元关系表达式，如 `corr(a, b)`、`ts_regression(y, x, d)`
- 如果一个表达式需要第二个独立收益来源才能成立，该候选直接作废
- 不生成同一 base expression 的正负孪生；方向不确定时先保留 canonical sign，在 K 记录方向证据
- 对可交换参数和反对称字段关系使用 canonical ordering，禁止靠等价表达式扩充数量
- 禁止仅用 `rank`、`zscore`、`scale` 等外层包装制造结构差异
- VECTOR reduction、Group 输入和字段单位必须符合 H 的契约
- PYTHON alpha 不许用逐元素 `for` 循环构建信号，时间复杂度不得超过 O(n)，优先使用 NumPy 向量操作
- 候选必须服务本轮已声明的个体机制问题；不得在 I 临时改成模板族参数网格

## operator 参数硬约束

- `ts_quantile(x, d, driver='gaussian')`，字符串参数必须用单引号
- `kth_element(x, d, k=?)`
- `ts_theilsen(x, y, d)`
- `ts_weighted_decay(x, k=0.5)`，`k` 不可省略
- `hump_decay(x, p=0)`，`p` 不可省略
- `group_mean(x, weight, group)`，`weight` 不可省略，可填 `1`
- `ts_target_tvr_decay(x, lambda_min=0, lambda_max=1, target_tvr=0.1)`
- `ts_target_tvr_hump(x, lambda_min=0, lambda_max=1, target_tvr=0.1)`
- `ts_poly_regression(y, x, d, k=1)`，`k` 不可省略

## 表达式输出要求

`expression_candidates.json` 中每条候选至少包含：

- `field_id`
- `dataset_id`
- `mechanism_id`
- `single_mechanism`
- `expression`
- `language`
- `settings`
- `why_not_mixed_signal`
- `source_mechanism_refs`
- `candidate_index`
- `hypothesis_delta`
- `operator_count`
- `field_count`

`simulation_batch.json` 必须是 `wqb sim create --input` 可直接读取的 payload，并与 expression candidate 一一对应。

## 成功条件

- I 输出的候选可以直接进入 J 回测
- 每条候选都能追溯到 H 的字段意义和机制解释
- 每条候选都通过 operator 与参数规范检查
- 候选数不超过 `iteration_plan.json` 的上限
- 全局 expression 唯一，且没有 canonical-equivalent 重复

## 明确边界

I 负责：
- 把机制翻译成表达式
- 做语法与 operator 检查
- 组织回测批次候选

I 不负责：
- 再次选字段
- 再次定义字段经济学意义
- 再次做社区、文档、平台、论文主搜索
- 为了过指标临时拼第二机制

## 下一跳

- `J 同步回测`
