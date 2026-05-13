# H_经济学机制假设

## Role
- combine theme context, main tower, candidate fields, internal experience, and external material
- produce executable economic mechanism hypotheses
- output mechanisms, not expressions

## Upstream
- `B_主题_平台机会`
- `D_选主塔`
- `E_数据与字段可行性`
- `F_社区_帮助中心经验`
- `G_外部资料_论文_用户材料`
- `K_结果诊断` (when rolling back)

## Downstream
- `I_表达式候选集`

## Inputs
### Necessary
- `B` platform theme and opportunity context
- `D` main tower tuple:
  - `region`
  - `delay`
  - `category`
- `E` outputs:
  - `candidate datafields`
  - `banned datafields`
  - `preferred datasets`
- `F` internal experience material
- `G` external material:
  - papers
  - user-provided articles
  - other relevant outside research
- official metadata for relevant fields

### Optional
- `K` failure feedback:
  - quality weak
  - turnover too low
  - which family was stronger:
    - gap
    - gate
    - level
    - dispersion

## Outputs
### Necessary
- `stepnum_node_H_mechanism_hypotheses/field_metadata__{REGION}_D{DELAY}_{CATEGORY}.json`
- `stepnum_node_H_mechanism_hypotheses/mechanism_hypotheses__{REGION}_D{DELAY}_{CATEGORY}.json`
- `stepnum_node_H_mechanism_hypotheses/node_summary.md`

### Optional
- mechanism priority ranking
- notes for how the next expression batch should change after `K`

## Success Criteria
- each mechanism has:
  - economic logic
  - main-tower fit reason
  - linked fields
  - internal experience support
  - external evidence support when relevant
- if entered from `K`, the mechanism update clearly reflects what got stronger or weaker

## Failure Criteria
- mechanisms are only field descriptions without economic meaning
- mechanisms are disconnected from:
  - main tower
  - field library
  - internal experience
  - external material
