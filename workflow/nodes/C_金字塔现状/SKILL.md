---
name: C-金字塔现状
description: 获取当前季度金字塔、全部金字塔和金字塔乘数。仅用于研究主图中的“C 金字塔现状”节点：读取当前季度各塔 alphaCount、全部塔分布和 multiplier，为后续选主塔提供成熟竖向塔、接近点亮塔、远离 D0 和 category 占比判断。不要在这个节点查看自己的 alpha 池、数据集、字段或表达式。
---

# C 金字塔现状

只做金字塔状态扫描。

## 允许使用的工具
- `wqb_core/user/get_pyramid_alphas.py`
- `wqb_core/user/get_pyramid_multipliers.py`

## 禁止事项
- 不要查看自己的 alpha 池。
- 不要开始看 dataset / datafield。
- 不要在这个节点写表达式。

## 输入
- `RUN_DIR`
  - 本轮研究产物目录。
- 可选：
  - `QUARTER`
  - `YEAR`

## 标准产物
- `02_pyramid/current_quarter_pyramids.json`
- `02_pyramid/all_pyramids.json`
- `02_pyramid/multipliers.json`
- `02_pyramid/node_summary.md`

## 成功标准
- 能拿到当前季度塔位提交数。
- 能拿到全部塔位分布。
- 能拿到 multiplier 数据。
- 能明确指出接近点亮的塔、成熟竖向塔和高价值塔。

## 输出要求
`node_summary.md` 至少写清：
- 本节点用了哪些命令
- 当前季度范围
- 哪些塔接近点亮
- 哪些竖向塔更成熟
- 哪些方向应尽量远离 D0
- 对下一个节点的输入建议

## 命令示例
```bat
run.bat "U:\Project\MainCode\3.Work\WQB\wqb_cli\docs\research_runs\2026-05-06_restart_workflow"
```
