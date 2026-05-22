# H 经济学机制假设

## 目标

综合 B/D/E/F/G 和 K 回退信息，形成可以转成表达式的经济学机制假设。

## 输入

必要：

- B 的 `level_gap.md`。
- D 的 `main_tower.json`。
- F 的 `candidate_datafields.json`。
- G 的 `community_lessons.md` 与 `platform_docs_lessons.md`。

可选：

- E 的 `super_constraints.json`。
- K 的 `diagnosis.md`。

## 只允许的 CLI

```powershell
wqb data field <field_id> --output <node_dir>/field_meta__field.json
wqb data operators --output <node_dir>/operators.json
wqb community search <mechanism_keyword> --limit 10 --output <node_dir>/mechanism_community.json
wqb community search <template_keyword> --limit 10 --output <node_dir>/template_community.json
wqb community search <paper_keyword> --limit 10 --output <node_dir>/paper_community.json
```

## 输出

必要：

- `mechanism_hypotheses.json`：机制、字段、方向、预期失败模式。
- `mechanism_priority.md`：排序理由。
- `node_summary.md`

可选：

- `field_meta__*.json`
- `mechanism_community.json`
- `template_community.json`
- `paper_community.json`

## 成功条件

- 每个机制都能明确映射到候选字段和表达式构造方向。
- 明确为什么该机制服务当前主塔或 super 约束。
- 明确记录 agent 实际搜过哪些社区模板、研报线索或论文线索，以及最终为什么选当前机制而不是其他模板。

## 下一跳

- `I 表达式候选集`
## 硬规则：单一经济机制

- H 只能提出单一主机制假设，不能把多个独立收益来源拼接成一个候选。
- 禁止把模型稳定性、模型修正、短期反转、流动性、波动率等多个独立机制用固定权重相加。
- 允许围绕同一主机制做非线性处理、同字段时间平滑、幂次、分段或门控，但这些都必须服务于同一个因果链，不能形成第二个独立收益来源。
- 允许在同一主机制内部提出多元关系假设，例如字段-字段相关性、字段对收益/价格行为的回归关系、同机制内部的交互项；但必须能解释为同一条经济学因果链。
- 机制假设必须说明主因果链条：为什么该字段或价格行为会带来收益。
- 风险控制可以存在，但必须是门控、中性化或过滤，不能作为独立 alpha 信号贡献主要收益。

## 搜索义务：社区模板、研报与论文

- H 不是直接套固定模板，而是必须先主动搜索社区中最接近当前字段/机制/塔目标的模板帖子，再决定机制假设。
- H 必须同时搜索研报与论文线索；如果本地社区库里有论文复现、研报摘要、Alpha 灵感贴，优先把这些当作经济学解释来源。
- H 在搜索论文前，必须先检查当前环境里是否已有 `arxiv_cli` 或等价 arXiv CLI；如果有，优先使用；如果没有，再退回其他可行工具进行论文搜索。
- 对每个候选机制，H 必须回答三个问题：社区里最像的模板是什么；它背后的经济学含义是什么；为什么该模板适合当前 datafield / 当前塔。
- 如果搜索后发现最相关模板依赖的是另一条独立机制，H 应回退并重选机制，而不是直接把模板硬拼到当前字段上。
- 对 MODEL 塔，H 必须优先搜索“model / template / corr / regression / non-linear / alpha 灵感 / paper / research”这一类关键词，再决定是否做稳定性、关系量、非线性或交互型机制。
