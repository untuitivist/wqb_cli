# I 表达式候选集

## 目标

I 只回答一件事：把 H 已经确认的字段机制翻译成可回测表达式，并检查 operator 与语法约束。

I 不重新做字段筛选，不重新做机制搜索，不把 H 和 F 的工作混进来。

## 输入

必要：
- H 的 `field_meanings.json`
- H 的 `mechanism_hypotheses.json`
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
- `expression_candidates.json`
- `operator_constraints_check.md`
- `node_summary.md`

可选：
- `operators.json`
- `simulation_create_doc.md`
- `field_meta__*.json`

## 表达式构建规则

- 每条候选必须绑定到单一主机制：`single_mechanism=true`
- 禁止线性混合多个独立收益信号
- OperatorCount < = 5, FieldCount < = 2
- 允许单一机制下的：
  - 同字段时间平滑
  - 同字段非线性变换
  - 同字段关系量
  - 同机制内部的多元关系表达式，如 `corr(a, b)`、`ts_regression(y, x, d)`
- 如果一个表达式需要第二个独立收益来源才能成立，该候选直接作废
- python alpha不许使用for等循环进行表达式构建, 时间复杂度不能超过O(n), 直接用numpy函数

## 研究策略目录

I 根据实时 Operator 清单提供以下策略；缺少所需 Operator 的策略不得生成：

- 单字段变化：`ts_delta(a, 22/63/126)`
- 单字段异常度：`ts_zscore(a, 22/63/126)`
- 变化新近性：`days_from_last_change(a)`
- 双字段关系：`ts_corr(a, b, 22/63/126)`
- 双字段回归：`ts_regression(a, b, 63/126)`
- 条件状态切换：`if_else(b > ts_mean(b, d), a, -a)`

候选必须测试时间变化、关系量、组内相对值或条件机制。以下表达式不能进入 J：

- 原始字段
- `rank(field)`
- `log(field)` 或其他仅改变尺度的表达式
- 同时堆叠多个 `rank/zscore/normalize/quantile/scale` 的表达式
- 依赖两个互不相关经济机制的字段组合

如果模型没有生成研究质量合格的候选，I 进入模型暂停状态，不得自动补充基线表达式。

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
- `template_id`
- `template_type`
- `strategy_family`
- `field_ids`
- `operator_names`

## 成功条件

- I 输出的候选可以直接进入 J 回测
- 每条候选都能追溯到 H 的字段意义和机制解释
- 每条候选都通过 operator 与参数规范检查

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

- `J 并行回测`
# Runtime lifecycle invariants

- Every H mechanism is persisted as an independent research idea.
- One I invocation plans and materializes expressions for exactly one idea. The Planner context contains that idea, its fields, available operators, and its latest validation error only.
- A successful idea moves from `PENDING_INSPECT` through `INSPECTING` to `READY`; the normal generation target is 4-10 distinct expressions per idea.
- Empty or invalid output marks only that idea as `ERROR`. Other ideas continue immediately. When all remaining ideas are cooling down, I waits briefly and retries instead of pausing the run.
- I routes to itself until every non-aborted idea has at least four validated expressions. Planner failure, timeout, invalid output, or an interrupted attempt uses deterministic local template expansion for the remaining shortfall instead of pausing the run or calling Planner again for that idea. User retry and abort decisions are durable.
