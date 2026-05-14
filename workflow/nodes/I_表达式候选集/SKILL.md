"""
功能概述
`I_表达式候选集` 节点负责把 H 节点的经济学机制假设翻译成第一批可回测表达式候选。

它的输入来自：

- `D -> I`：主塔范围与基础 settings 约束
- `E -> I`：candidate datafields 与 preferred datasets
- `F -> I`：站内经验对 analyst 数据的结构偏好
- `H -> I`：正式机制假设

它的输出不是回测结果，而是：

- 第一批表达式候选
- 可直接传给 `simulate` / `concurrent_simulate` 的 payload
- 每条表达式对应的机制、字段与约束说明

主推荐入口

- `run.bat`

输出

- `all_operators.json`
- `expression_candidates__{REGION}_D{DELAY}_{CATEGORY}.json`
- `simulation_batch__{REGION}_D{DELAY}_{CATEGORY}.json`
- `node_summary.md`

约束

- 必须以经济机制优先，不允许先写式子再找解释。
- 不重复定义变量；优先单行最终表达式。
- `fieldCount <= 2`。
- `operatorCount <= 5`。
- 优先低换手，偏好 `ts_mean`、`ts_decay_linear` 等较长窗口。
- 默认使用风险中性化，并说明原因。
- 使用的 field 必须来自 E 节点产出的 candidate datafield 库。
- 使用过的 `datafield` 不能再用。
- 使用过的 `dataset` 尽量不要再用。
- 先保证 OS / 分析数据差的 dataset 不进入表达式阶段。
- 优先简单稳健结构，避免超过 2 到 3 层的深嵌套。
- 可用 `tradewhen`、`ifelse`、`tanh`、`sigmoid`、`arc_tan`、`s_log_1p` 等做低相关设计，但仍需满足 operator 数约束。
- 不需要加残差或除零保护项。
- 必须尊重 datafield type；若后续出现 vector field，则必须先经 vec\_op 变成 matrix 后再进入其他算子。
- 尽可能使用没有使用过的operators, 在此文件夹下有`当前operators使用情况.md`

