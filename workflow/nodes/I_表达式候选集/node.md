# I_表达式候选集

## Role
- 把机制假设翻译成第一批或下一批可回测表达式。
- 同时拉取当前全部 operator，显式记录表达式构建规则。

## Upstream
- `H_经济学机制假设`

## Downstream
- `J_并行回测`

## Inputs
### Necessary
- `H` 的机制假设
- `E` 的 candidate datafields
- 当前主塔设置
- 表达式构建规则：
  - economic rationale first
  - `fieldCount <= 2`
  - `operatorCount <= 5`
  - 慢信号优先
  - 风险中性化默认开启
  - 遵守 field type
  - 不重复定义变量
  - 最后一行是最终表达式

### Optional
- `K` 的回退反馈
- 当前 operator 全量参考

## Outputs
### Necessary
- `07_I_expression_candidates/all_operators.json`
- `07_I_expression_candidates/expression_candidates__{REGION}_D{DELAY}_{CATEGORY}.json`
- `07_I_expression_candidates/simulation_batch__{REGION}_D{DELAY}_{CATEGORY}.json`
- `07_I_expression_candidates/node_summary.md`

### Optional
- 主批次/副批次区分
- 第二批改良表达式备注

## Success Criteria
- 产出一批满足规则的表达式候选。
- 产出可直接送入 `J` 的 simulation batch。

## Failure Criteria
- 表达式违反 field/operator 约束。
- 没有把机制真正翻译成结构化候选。
