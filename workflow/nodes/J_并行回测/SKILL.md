"""
功能概述
`J_并行回测` 节点负责把 I 节点产出的表达式候选批次送入平台并行回测。

它的输入来自：
- `I -> J`：simulation batch 与表达式候选说明

它的输出包括：
- 第一批实际回测请求
- 回测原始响应
- 提取后的 alpha id 与表达式映射
- 节点摘要

主推荐入口
- `run.bat`

输出
- `primary_batch__{REGION}_D{DELAY}_{CATEGORY}.json`
- `concurrent_simulate__{REGION}_D{DELAY}_{CATEGORY}.json`
- `alpha_candidates__{REGION}_D{DELAY}_{CATEGORY}.json`
- `node_summary.md`

约束
- 默认先只跑主候选，不一次性把整批全压上去。
- 非 `GLB` 默认使用 `10(m) * 8(c)`。
- `GLB` 默认使用 `5(m) * 4(c)`。
- 使用命令行参数调用 `wqb_core` 的并行回测入口。
- 回测批次应保持同塔、同 region、同 delay、同 category。
"""
