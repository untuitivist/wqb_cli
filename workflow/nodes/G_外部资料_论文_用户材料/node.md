# G_外部资料_论文_用户材料

## Role
- 基于主塔与候选 datafields 收集站外论文与研究材料
- 为 `H_经济学机制假设` 提供外部证据

## Upstream
- `D_选主塔`
- `E_数据与字段可行性`

## Downstream
- `H_经济学机制假设`

## Inputs
### Necessary
- `D` 的主塔三元组：
  - `region`
  - `delay`
  - `category`
- `E` 的 `available_datafields__{REGION}_D{DELAY}_{CATEGORY}.json`

### Optional
- 用户提供论文 / 文章 / 笔记

## Outputs
### Necessary
- `stepnum_node_G_external_material/queries__{REGION}_D{DELAY}_{CATEGORY}.json`
- `stepnum_node_G_external_material/arxiv_results__{REGION}_D{DELAY}_{CATEGORY}.json`
- `stepnum_node_G_external_material/external_material_summary__{REGION}_D{DELAY}_{CATEGORY}.json`
- `stepnum_node_G_external_material/node_summary.md`

### Optional
- 用户材料索引
- 外部证据优先级排序

## Success Criteria
- 外部检索 query 与主塔及候选 field 语义相关
- 至少形成一组可支撑 analyst 机制的外部论文结论
- 输出可直接供 `H` 使用

## Failure Criteria
- 没有实际调用 arXiv API
- 查询结果与 analyst / forecast / target price / revision 主线脱节
- 只给原始论文列表，没有形成摘要结论
