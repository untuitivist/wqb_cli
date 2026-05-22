# H 经济学机制假设

## 目标

H 只回答一件事：`候选 datafield 到底在表达什么经济学含义，这个含义有没有社区/论文证据支持，是否值得进入表达式构建。`

H 不负责拼表达式，不负责调 operator，不负责回测参数。

## 输入

必要：
- B 的 `level_gap.md`
- D 的 `main_tower.json`
- F 的 `candidate_datafields.json`
- G 的社区/文档经验产物

可选：
- E 的 `super_constraints.json`
- K 的 `diagnosis.md`

## 先后顺序

H 必须严格按下面顺序执行：

1. 读取 F 输出的候选字段池，不先发明机制。
2. 用 `wqb data field <field_id>` 读取字段描述、dataset、category、coverage。
3. 基于字段描述提炼 1 到 3 个机制关键词。
4. 先搜社区，再搜论文。
5. 最后才形成机制假设。

## 允许的 CLI

```powershell
wqb data field <field_id> --output <node_dir>/field_meta__<field_id>.json
wqb community search <keyword> --limit 10 --output <node_dir>/community__<field_id>__<keyword>.json
python -m arxiv_cli search query --all <keyword> --max-results 10 --sort-by relevance --output <node_dir>/arxiv__<field_id>__<keyword>.json
```

说明：
- 论文搜索必须优先使用 `python -m arxiv_cli ...`
- 只有 `arxiv_cli` 不可用或接口失败时，才允许退回其他工具

## 输出

必要：
- `field_meanings.json`
- `mechanism_hypotheses.json`
- `mechanism_priority.md`
- `node_summary.md`

可选：
- `field_meta__*.json`
- `community__*.json`
- `arxiv__*.json`

## 字段筛选规则

- H 只处理 F 已经放进候选池的字段。
- H 可以淘汰字段，但不能新增未经过 F 的字段。
- H 必须优先淘汰“字段描述不清、机制无法解释、外部证据太弱”的字段。
- H 必须明确区分“字段名称像模型”与“字段经济学含义清楚”。
- 对 `MODEL` 塔，优先保留描述明确的传统机制字段，如估值、成长、surprise、分析师修正、质量、动量；谨慎对待纯黑盒 `dl/nugget/predict` 风格字段。

## 社区与论文搜索义务

对每个候选字段，H 至少要回答四个问题：

1. 这个字段的官方描述是什么？
2. 这个字段最像哪类社区模板或社区机制讨论？
3. 这类机制在论文里通常对应什么经济学故事？
4. 它为什么适合当前 tower，而不是别的字段更适合？

搜索要求：
- 社区搜索关键词必须从字段描述出发，而不是只搜字段 id。
- 论文搜索关键词必须是机制词，如 `free cash flow to price`、`earnings surprise`、`analyst revision`、`inventory change`、`price momentum`。
- 如果社区模板与论文逻辑互相冲突，优先保守，降低该字段优先级。

## 成功条件

- `mechanism_hypotheses.json` 中每条机制都明确绑定到具体字段。
- 每条机制都带有至少一条社区证据和一条论文证据，或清楚记录为什么论文证据不足。
- H 输出后，I 可以在不重新解释经济学含义的前提下直接构造表达式。

## 明确边界

H 负责：
- 选字段意义
- 查字段描述
- 搜社区
- 搜论文
- 给机制解释
- 做字段优先级排序

H 不负责：
- 写 alpha 表达式
- 选 operator 细节
- 选 decay / truncation / neutralization
- 为了过指标而混机制

## 下一跳

- `I 表达式候选集`
