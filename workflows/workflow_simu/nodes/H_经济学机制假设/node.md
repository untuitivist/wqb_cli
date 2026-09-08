# H 可检验机制契约

## 目标

H 把字段意义和 G 的证据收敛成可证伪的机制契约：测量对象是什么、预期反应是什么、允许哪些同机制关系、哪些结果会否定该解释。

H 不负责写表达式，不负责调 operator，不负责调回测参数，也不能把未知单位或字段类型留给 I 猜测。

## 输入

必要：
- D 的 `main_tower.json`
- F 的 `candidate_datafields.json`
- G 的社区、文档、平台、论文检索产物

可选：
- G 的 `reality_evidence_index.json`；每个 `completed[]` 条目必须提供 `evidence_id` 与可直接验证的 `stored_path`
- B 的 `level_gap.md`
- E 的 `super_constraints.json`
- K 的 `diagnosis.md`

## 执行顺序

H 必须严格按下面顺序执行：

1. 读取 F 输出的候选字段池
2. 用 `wqb data field <field_id>` 读取字段描述、dataset、category、coverage 等信息
3. 基于字段描述提炼 1 到 3 个机制关键词
4. 读取 G 已完成的社区、文档、平台、论文检索结果
5. 如果 G 产生了 Wind reality evidence，先验证每个 `EvidenceRecord` 的 hash、provider contract version、实体代码、as-of/period、unit/source/warnings/completeness，再解释其支持边界
6. 验证字段类型、单位、coverage、缺失值编码和 VECTOR reduction 要求
7. 定义允许的单字段组件、同机制字段关系和禁止组合
8. 写出预期方向不确定性与可证伪条件
9. 形成机制契约与优先级

## Wind standing

H 的 Wind standing 是 **supplemental**，不是第二个 G。

- 默认只消费 G 已经形成的 Wind `EvidenceRecord`。
- 如果某个现有 evidence 的实体、报告期或口径存在一个可以通过单次查询消除的关键歧义，允许创建一个**独立的 H clarification plan**；它必须复用同一 `RUN_ID` 与同一 `research_freeze.json`，只包含该 clarification check，并重新通过 fresh balance + cost profile + `plan-check` 后由 `execute-plan` 执行。
- 不得把 G 已完成 checks 复制进新的 H plan；否则新 `plan_id` 会把旧请求视为未执行并产生重复调用风险。
- 如果缺口需要重新做多来源搜索、多个实体取数或新的机制族探索，必须回退 G；H 不得为了方便把 G 的工作搬进自己。
- H clarification 只能引用 frozen `mechanism_families.json` 中已有的 mechanism id，不能新增机制族。
- H 不得把 Wind 观察直接升级成 `BACKTEST_EVIDENCE`，也不得据此新增未经 F 的 BRAIN 字段。

## 证据 standing

H 应在机制契约中显式区分至少以下 standing：

- `BRAIN_FIELD_METADATA`
- `PRIMARY_DOCUMENT`
- `WIND_REALITY_OBSERVATION`
- `ACADEMIC_MECHANISM`
- `COMMUNITY_EXPERIENCE`
- `BACKTEST_EVIDENCE`（只有 J/K 之后才可能存在）

不同 standing 证明不同主张，不得合并成一个无语义 confidence score。

## 推荐 CLI

```powershell
# 读取字段元数据
wqb data field "close" --output <node_dir>/field_meta__close.json
wqb data field "volume" --output <node_dir>/field_meta__volume.json
wqb data field "vwap" --output <node_dir>/field_meta__vwap.json
wqb data field "returns" --output <node_dir>/field_meta__returns.json

# 验证 G 给出的 Wind evidence：从 reality_evidence_index.json 的 completed[].stored_path 读取实际记录路径
wqb evidence verify <completed.stored_path> --output <node_dir>/wind_verify__quality.json

# 只在一个关键歧义可用单次补查消除时，创建只含该 check 的独立 clarification plan
# plan 中必须复用同一 RUN_ID + research_freeze.json，不得复制 G 已完成 checks
wqb evidence wind plan-check `
  --input <node_dir>/wind_clarification_plan.json `
  --output <node_dir>/wind_clarification_plan_check.json
wqb evidence wind execute-plan `
  --input <node_dir>/wind_clarification_plan.json `
  --output <node_dir>/wind_clarification_evidence_index.json
```

说明：
- 论文搜索与社区搜索是 G 的职责，H 读取和解释这些结果
- 如果 H 发现 G 的证据不足，应回退 `G`，而不是自己跳过去把 G 和 H 混做

## 输出

必要：
- `field_meanings.json`
- `mechanism_hypotheses.json`
- `field_unit_contracts.json`
- `mechanism_contracts.json`
- `mechanism_priority.md`
- `reality_checks.json`
- `node_summary.md`

可选：
- `field_meta__*.json`
- `wind_verify__*.json`
- `wind_clarification_plan.json`
- `wind_clarification_plan_check.json`
- `wind_clarification_evidence_index.json`

`reality_checks.json` 中每条至少包含：

- `mechanism_id`
- `provider`
- `evidence_refs`
- `observation`
- `supports`
- `contradicts`
- `limitations`
- `standing`
- `provider_contract_version`
- `as_of_or_period`

## 字段筛选规则

- H 只处理 F 已经放进候选池的字段
- H 可以淘汰字段，但不能新增未经 F 的字段
- H 必须优先淘汰“字段描述不清、机制无法解释、外部证据太弱”的字段
- 对 `MODEL` 塔，优先保留描述明确的传统机制字段，如估值、成长、surprise、分析师修正、质量、动量
- 对纯 `dl/nugget/predict` 风格字段保持谨慎，除非已有很强的 H/K 证据链
- VECTOR 字段必须指定合法 reducer；整数标签不能因为名称像行业代码就假定为 Group
- 第二字段只允许作为同一机制的另一测量、条件变量或平台确认的 Group 输入

## 判断问题

对每个候选字段，H 至少要回答四个问题：

1. 官方字段描述是什么
2. 它最像哪类社区模板或社区机制讨论
3. 这类机制在论文里通常对应什么经济学故事
4. 为什么它适合当前 tower，而不是别的字段更适合

如果存在 Wind reality evidence，还必须回答第五个问题：

5. 现实观察对这个机制是支持、削弱、冲突还是仅提供背景；它的 provider/source/time/completeness 边界是什么

每条 `mechanism_contracts.json` 还必须包含：

- `mechanism_id`
- `field_ids`
- `measurement_roles`
- `single_mechanism_boundary`
- `expected_observation`
- `falsification_conditions`
- `direction_status`: `supported`、`uncertain` 或 `not_applicable`
- `allowed_relations`
- `forbidden_relations`
- `evidence_refs`
- `reality_evidence_refs`

## 成功条件

- `mechanism_hypotheses.json` 中每条机制都明确绑定到具体字段
- 每条机制都有来自 G 的社区证据、文档或平台证据、论文或研报证据
- 字段单位、VECTOR reduction 和 Group 输入均有明确契约
- 如果引用 Wind，每个 `evidence_id` 都通过完整性验证且只在其证明边界内使用
- H 输出后，I 可以在不重新解释经济学含义、猜测数据类型或再次查询 Wind 的前提下直接构造表达式

## 明确边界

H 负责：
- 读字段描述
- 解释字段经济学含义
- 判断机制是否成立
- 做字段优先级排序
- 解释已取得的现实观察对 falsification contract 的影响

H 不负责：
- 写 alpha 表达式
- 选 operator 细节
- 调 decay、truncation、neutralization
- 为了过指标临时拼第二机制
- 把 Wind 当成新的 BRAIN datafield universe

## 下一跳

- `I 小规模表达式候选`
