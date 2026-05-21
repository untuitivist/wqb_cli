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
```

## 输出

必要：

- `mechanism_hypotheses.json`：机制、字段、方向、预期失败模式。
- `mechanism_priority.md`：排序理由。
- `node_summary.md`

可选：

- `field_meta__*.json`
- `mechanism_community.json`

## 成功条件

- 每个机制都能明确映射到候选字段和表达式构造方向。
- 明确为什么该机制服务当前主塔或 super 约束。

## 下一跳

- `I 表达式候选集`
## 硬规则：单一经济机制

- H 只能提出单一主机制假设，不能把多个独立收益来源拼接成一个候选。
- 禁止把模型稳定性、模型修正、短期反转、流动性、波动率等多个独立机制用固定权重相加。
- 机制假设必须说明主因果链条：为什么该字段或价格行为会带来收益。
- 风险控制可以存在，但必须是门控、中性化或过滤，不能作为独立 alpha 信号贡献主要收益。
