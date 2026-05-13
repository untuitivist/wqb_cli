"""
功能概述
`H_经济学机制假设` 节点负责把多路输入收敛成一组正式、可执行的经济学机制假设。

它的输入来自：
- `B -> H`：主题 / 平台机会
- `D -> H`：主塔约束与当前主塔决策
- `E -> H`：candidate datafields / preferred datasets
- `F -> H`：站内社区与帮助中心经验

它的输出不是表达式，而是：
- 可写表达式的机制假设
- 每条假设对应的核心 field
- 每条假设的支持证据与风险

主推荐入口
- `run.bat`

输出
- `field_metadata__{REGION}_D{DELAY}_{CATEGORY}.json`
- `mechanism_hypotheses__{REGION}_D{DELAY}_{CATEGORY}.json`
- `node_summary.md`

约束
- 必须以官方 field description 为准。
- 不允许对 field 含义拍脑袋解释。
- 机制要服务当前主塔目标。
- 假设应优先围绕当前 candidate field 库展开。
"""
