## 功能概述
`F_社区_帮助中心经验` 节点负责把主塔和 `E` 节点产出的候选 `datafields` 转换成一批站内经验材料。

它不是机制节点，不直接生成经济学假设。  
它的职责是：
- 围绕主塔与候选 field 生成检索 query
- 在本地社区数据库里聚合 forum / docs 经验材料
- 输出后续 `H_经济学机制假设` 可直接使用的内部证据

## 输入
- `D_选主塔` 结果：
  - `region`
  - `delay`
  - `category`
- `E_数据与字段可行性` 结果：
  - `available_datafields__{REGION}_D{DELAY}_{CATEGORY}.json`

## 输出
- `queries__{REGION}_D{DELAY}_{CATEGORY}.json`
- `community_experience__{REGION}_D{DELAY}_{CATEGORY}.json`
- `node_summary.md`

## 约束
- 这里只做经验材料聚合，不做机制判断
- 先保留更泛化、可迁移的经验
- 不把 dataset id 本身当成主要 query
- 优先围绕 category 和高频 field 语义 token 做检索

## 当前主用途
- 为 `ANALYST` 这类主塔准备：
  - analyst
  - estimate
  - target price
  - EPS
  - EBITDA
  - revision
等主题下的站内经验材料
