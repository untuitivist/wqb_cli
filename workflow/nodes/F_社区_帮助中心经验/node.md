# F_社区_帮助中心经验

## Role
- 把主塔与 candidate fields 转成站内社区 / 帮助中心经验材料。
- 为后续机制节点提供内部经验支持，而不是直接生成表达式。

## Upstream
- `D_选主塔`
- `E_数据与字段可行性`

## Downstream
- `H_经济学机制假设`

## Inputs
### Necessary
- `D` 的主塔三元组
- `E` 的 candidate datafields / preferred datasets
- 本地社区库：
  - `wqb_core/dataset/forum/community.sqlite3`

### Optional
- 手工补充 query
- 对某些字段的定向社区关键词

## Outputs
### Necessary
- `05_F_community_experience/queries__{REGION}_D{DELAY}_{CATEGORY}.json`
- `05_F_community_experience/community_experience__{REGION}_D{DELAY}_{CATEGORY}.json`
- `05_F_community_experience/node_summary.md`

### Optional
- query 与命中结果的相关性备注
- 低质量 query 的噪声说明

## Success Criteria
- 形成可支撑机制判断的 analyst 经验材料集合。
- query 既包含主塔语义，也包含 candidate field 语义。

## Failure Criteria
- 只有泛搜索结果，没有和主塔/field 收敛。
- 经验材料无法支撑后续机制判断。
