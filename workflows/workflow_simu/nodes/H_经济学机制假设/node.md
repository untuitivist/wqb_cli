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
- B 的 `level_gap.md`
- E 的 `super_constraints.json`
- K 的 `diagnosis.md`

## 执行顺序

H 必须严格按下面顺序执行：

1. 读取 F 输出的候选字段池
2. 用 `wqb data field <field_id>` 读取字段描述、dataset、category、coverage 等信息
3. 基于字段描述提炼 1 到 3 个机制关键词
4. 读取 G 已完成的社区、文档、平台、论文检索结果
5. 验证字段类型、单位、coverage、缺失值编码和 VECTOR reduction 要求
6. 定义允许的单字段组件、同机制字段关系和禁止组合
7. 写出预期方向不确定性与可证伪条件
8. 形成机制契约与优先级

## 推荐 CLI

```powershell
# 读取字段元数据
wqb data field "close" --output <node_dir>/field_meta__close.json
wqb data field "volume" --output <node_dir>/field_meta__volume.json
wqb data field "vwap" --output <node_dir>/field_meta__vwap.json
wqb data field "returns" --output <node_dir>/field_meta__returns.json

# arxiv-cli - 注意：论文搜索主要是 G 的职责
# 如果 H 读取 G 的结果，只有 G 证据不足时才补搜
arxiv --help
arxiv search query --help
arxiv search raw --help

# arxiv-cli - 补充搜索机制关键词（如果 G 不够）
arxiv search query --all "momentum" --category q-fin.ST --max-results 10 --sort-by relevance --output <node_dir>/arxiv__momentum.json
arxiv search query --all "volatility" --category q-fin.ST --max-results 10 --sort-by relevance --output <node_dir>/arxiv__volatility.json

# arxiv-cli - 复杂查询特定机制
arxiv search raw "cat:q-fin.ST AND (all:\"price momentum\" OR all:\"momentum factor\")" --max-results 8 --sort-by relevance --output <node_dir>/arxiv__momentum_mechanism.json

# arxiv-cli - 先 dry-run 预览
arxiv search query --all "momentum" --category q-fin.ST --dry-run
arxiv search raw "cat:q-fin.ST AND (all:\"price momentum\" OR all:\"momentum factor\")" --dry-run

# arxiv-cli - 文本格式快速检查
arxiv search raw "cat:q-fin.ST AND (all:\"price momentum\" OR all:\"momentum factor\")" --max-results 5 --format text
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
- `node_summary.md`

可选：
- `field_meta__*.json`

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

## 成功条件

- `mechanism_hypotheses.json` 中每条机制都明确绑定到具体字段
- 每条机制都有来自 G 的社区证据、文档或平台证据、论文或研报证据
- 字段单位、VECTOR reduction 和 Group 输入均有明确契约
- H 输出后，I 可以在不重新解释经济学含义或猜测数据类型的前提下直接构造表达式

## 明确边界

H 负责：
- 读字段描述
- 解释字段经济学含义
- 判断机制是否成立
- 做字段优先级排序

H 不负责：
- 写 alpha 表达式
- 选 operator 细节
- 调 decay、truncation、neutralization
- 为了过指标临时拼第二机制

## 下一跳

- `I 小规模表达式候选`
