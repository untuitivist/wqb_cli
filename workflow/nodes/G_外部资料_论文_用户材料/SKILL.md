## 功能概述
`G_外部资料_论文_用户材料` 节点负责基于 `D` 的主塔与 `E` 的 candidate datafields 收集外部研究材料。
它与 `F_社区_帮助中心经验` 并列，为 `H_经济学机制假设` 提供站外证据。

职责：
- 读取主塔与候选 datafields
- 生成 analyst 主题相关的外部检索 query
- 通过 arXiv API 获取论文结果
- 结合可选用户材料，输出可供 `H` 直接消费的外部证据摘要

## 输入
- `D_选主塔` 结果：
  - `region`
  - `delay`
  - `category`
- `E_数据与字段可行性` 结果：
  - `available_datafields__{REGION}_D{DELAY}_{CATEGORY}.json`

## 输出
- `queries__{REGION}_D{DELAY}_{CATEGORY}.json`
- `arxiv_results__{REGION}_D{DELAY}_{CATEGORY}.json`
- `external_material_summary__{REGION}_D{DELAY}_{CATEGORY}.json`
- `node_summary.md`

## 约束
- 必须通过正式 `arXiv API` 脚本取数
- 默认按“无用户资料”处理，除非当前 run 明确提供用户材料文件
- 只做外部证据聚合，不直接生成机制或表达式
- 输出要能直接支持 `H` 的经济学机制假设
