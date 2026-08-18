# H 机制组件与模板族

## 目标

把 E 的字段契约和 G 的证据组织成带字段角色的 mechanism components，再按 `template_contract.md` 定义经济上不同、可枚举、可去重的 template family specifications。

H 定义 population，不实例化最终 candidate，也不选择回测结果方向。

## 输入

- D 的 `field_sampling_frame.json` 与 `dataset_caps.json`
- E 的全部 contracts 与 operator inventory
- F 的 allocation/randomization plan
- G 的 evidence 和 family design constraints

## 三层结构

1. `component`：一个字段或同机制字段组，以及必要的 missing handling、winsorization 或 VECTOR reduction。
2. `core_relation`：创新、持续性、加速度、残差、spread、covariance、regression、coherence、lead-lag 等一个可解释比较关系。
3. `restrained_detail`：只有证据允许时加入的 peer grouping、门控或单调非线性；不得只是换外层 wrapper。

每个 family 必须有可证伪的经济解释。复杂度来自不同关系、时间状态、分布状态和同机制交互，而不是无意义地增加 operator 数量。

## 输出

- `mechanism_contracts.json`
- `component_catalog.json`
- `template_family_specs.json`
- `template_catalog.md`：严格采用 `[English Name] - 中文名 / 逻辑 / 模板` 格式。
- `template_format_validation.json`
- `family_population_estimates.json`
- `family_coverage_matrix.json`
- `family_review.md`
- `commands.md`
- `node_summary.md`

## Component contract

每个 component 至少包含：

- `component_id`、`mechanism_id`、`field_ids`、`field_roles`
- `arity`：按唯一字段数计算的 unary、binary 或 ternary
- `preprocessor` 与每个 VECTOR reducer
- `unit_contract_refs`、`missing_contract_refs`、`evidence_refs`
- `single_mechanism_boundary`
- `allowed_group_inputs`
- `forbidden_combinations`

多字段 component 只能是同一机制的多种测量、条件变量或已确认 Group 输入。禁止把两个独立 return signal 线性拼接。

## Family contract

每个 family 至少包含：

- `template_family_id`、`template_version`、`template_epoch`、中英文名和中文逻辑
- `mechanism_ids`、允许 component 层级和 arity
- 完整模板源码、canonical AST skeleton 和 placeholder contracts
- `core_relation` 与经济解释
- 参数 domain、窗口顺序和合法组合约束
- operator/field count bounds
- sign policy、commutative ordering 和 antisymmetric orientation
- population size 计算方法
- expected failure modes 与 evidence refs

模板源码必须包含两行 header、唯一 `_variable` 中间变量、最后一次 `template_LLM` 赋值和最终 `template_LLM` 行。每个 placeholder 必须声明 type/dimension/unit/domain；VECTOR reducer 和 Group 输入必须引用 E 的明确 contract。

## 去重与相关性前置约束

- 方向不确定时只保留 canonical sign；不同时生成 exact inverse twin。
- 可交换参数排序，`short_window < long_window` 等约束必须写进 family，而不是生成后再去重。
- 反对称 spread 只保留 canonical field orientation；只有非等价的回归方向或 lead-lag 方向可以双向保留。
- `rank`、`scale`、`zscore`、`normalize` 的单纯替换不得拆成多个 family。
- 结构预去重只减少必然冗余，不能声称真实 PnL 低相关。

## 成功条件

- 每个 family 都能枚举有限有效 population，且 population 足以支持 F 的配额或明确标为 census。
- 所有字段、operator、reducer 和 Group 输入都能回溯到 E。
- family 间核心关系确实不同，没有 wrapper-only family。
- `template_format_validation.json.verdict = true`，模板目录与 family specs 一一对应。

## 下一跳

- `I 候选生成与 manifest`
