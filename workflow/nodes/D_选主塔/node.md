# D\_选主塔

## Role

- 依据主题与金字塔现状，选择当前研究主塔。
- 这是 skill-only 决策节点，不负责执行回测或抓取数据。

## Upstream

- `B_主题_平台机会`
- `C_金字塔现状`

## Downstream

- `E_数据与字段可行性`
- `F_社区_帮助中心经验`
- `H_经济学机制假设`

## Inputs

### Necessary

- `01_theme/messages_summary.json`
- `01_theme/events.json`
- `02_pyramid/current_quarter_pyramids.json`
- `02_pyramid/all_pyramids.json`
- `02_pyramid/multipliers.json`
- 主塔选择约束规则：
  - 点塔第一优先级 (本季度提交满3个即为点亮)
  - `fundamental` 同竖向塔占比 `< 15%`
  - 优先成熟竖向塔
  - 新开地区要成列推进
  - 尽量远离 `D0`

### Optional

- 主题加分判断
- 第二候选塔比较结果

## Outputs

### Necessary

- `03_D_main_tower/decision.json`
- `03_D_main_tower/node_summary.md`
- 明确的主塔三元组：
  - `region`
  - `delay`
  - `category`

### Optional

- 第二候选塔
- 被拒绝候选及理由

## Success Criteria

- 唯一确定本轮主塔。
- 理由能解释点塔优先级与硬约束的满足情况。

## Failure Criteria

- 主塔结论依赖了不允许的输入。
- 没有明确给出 `region / delay / category`。

