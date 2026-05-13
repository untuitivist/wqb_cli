---
name: E-数据与字段可行性
description: 围绕已选主塔评估 dataset 与 datafield 可行性。这个节点开始使用自己的 Alpha 池 / 研究地图约束，但仍不生成表达式。优先级必须严格遵守：1. OS(out of sample) 效果差的 dataset 不要用；2. 使用过的 datafield 不能再用；3. 使用过的 dataset 最好不要再用。
---

# E 数据与字段可行性
这是一个执行节点。

## 输入来源
- `D_选主塔`
- `自己的 Alpha 池 / 研究地图`
- `docs/data_all`

## 必须遵守的优先级
1. 在分析数据中 OS(out of sample) 效果差的 dataset 不要用
2. 使用过的 datafield 不能再用
3. 使用过的 dataset 最好不要再用

## 当前额外约束
- 多样性很重要
- 已使用 datafield 是硬约束，必须排除
- 已使用 dataset 尽量排除
- 只围绕当前主塔工作
- 此节点不生成表达式

## 标准产物
- `active_tower_alphas__{TAG}__WQBRAIN.json`
- `used_fields_by_alpha__{TAG}.json`
- `dataset_screening_step1__{TAG}.json`
- `node_summary.md`

## 禁止事项
- 不要跳到表达式设计
- 不要在未完成 dataset/datafield 约束前开始回测
- 不要忽略 `docs/data_all` 的分析结果
