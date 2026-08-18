# F 分层抽样设计

## 目标

在看到回测结果前固定 family 层的抽样、随机化、denominator 和统计规则，使首轮筛选测量“族密度”而不是候选生成器偏好。

## 输入

- B 的 `family_screen_contract.json`
- B 的 `quality_gates.json`
- C 的 `settings_identity.json`
- D 的 `dataset_caps.json`
- E 的全部 field/operator contracts

## 输出

- `allocation_plan.json`
- `randomization_plan.json`
- `analysis_contract.json`
- `family_budget.json`
- `denominator_rules.md`
- `commands.md`
- `node_summary.md`

## 初筛设计

- family 先等额分配，使用固定 seed 从各族完整有效 population 中无放回抽样。
- 默认研究参考是每族约 `80` 个独立 candidate；具体值必须由总预算、族数、最小有效样本和族内 population 支持。
- 族内有效 population 小于配额时，使用全部 population 并显式标记 census；不得重复采样凑数。
- unary、binary、ternary 和不同 mechanism tier 可以分层，但层权重必须在 I 生成前固定。
- 初筛不能因为某个 family 看起来熟悉就提前给更多预算。

## 预注册统计口径

- `execution_ready_rate = READY / assigned`
- `quality_density = quality_pass / READY`
- `usable_density = quality_and_checks_pass / assigned`
- 每个比例报告 numerator、denominator 和 Wilson interval。
- auth、throttle、平台中断与 family 确定性错误分开报告。
- IS-PnL 聚类的相关系数、最小重叠长度、缺失处理和 cluster threshold 必须预先写入 `analysis_contract.json`。

## 成功条件

- 任一候选生成前，样本量、seed、分层、门槛和相关性算法都已冻结。
- 总预算由计划推导，不以 5000 作为默认目标。
- expansion budget 尚未分配给具体 family。

## 下一跳

- `G 模板群证据`
