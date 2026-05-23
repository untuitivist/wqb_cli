# H 经济学机制假设

## 目标

H 只回答一件事：候选字段到底在表达什么经济学含义，这个含义有没有社区、文档、平台资料和论文证据支持，以及它是否值得进入表达式构建。

H 不负责写表达式，不负责调 operator，不负责调回测参数。

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
5. 判断字段经济学含义是否清晰、证据是否足够、是否适配当前 tower
6. 形成机制假设与优先级

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

## 判断问题

对每个候选字段，H 至少要回答四个问题：

1. 官方字段描述是什么
2. 它最像哪类社区模板或社区机制讨论
3. 这类机制在论文里通常对应什么经济学故事
4. 为什么它适合当前 tower，而不是别的字段更适合

## 成功条件

- `mechanism_hypotheses.json` 中每条机制都明确绑定到具体字段
- 每条机制都有来自 G 的社区证据、文档或平台证据、论文或研报证据
- H 输出后，I 可以在不重新解释经济学含义的前提下直接构造表达式

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

- `I 表达式候选集`
