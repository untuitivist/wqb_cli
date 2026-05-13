---
name: 获取主题-平台机会
description: 获取当前平台上的近期主题、活动和平台机会。仅用于研究工作图中的“获取主题 / 平台机会”节点：读取消息摘要、完整消息首页和公开活动，识别近期明确的 region theme、competition、thematic opportunity 或 platform update。不要在这个节点进入金字塔、数据集、字段、alpha 池、表达式或回测。
---

# 获取主题 / 平台机会

只做“平台最近在推什么、哪些方向值得优先关注”的扫描。

## 允许使用的工具
- `wqb_core/user/get_messages_summary.py`
- `wqb_core/user/get_messages.py`
- `wqb_core/community/get_events.py`

## 禁止事项
- 不要查看金字塔、塔位、数据集、字段或 alpha 池。
- 不要生成表达式。
- 不要在本节点决定最终研究塔。

## 输入
- `RUN_DIR`
  - 本轮研究产物目录。
- 可选：
  - `MESSAGES_SUMMARY_LIMIT`
  - `MESSAGES_FULL_LIMIT`
  - `MESSAGES_OFFSET`

## 标准产物
- `01_theme/messages_summary.json`
- `01_theme/messages_full.json`
- `01_theme/events.json`
- `01_theme/node_summary.md`

## 执行顺序
1. 拉 `messages_summary`
2. 拉 `messages` 首页
3. 拉 `events`
4. 写本节点总结

## 输出要求
`node_summary.md` 至少写清：
- 本节点用了哪些命令
- 命中了哪些近期主题、比赛或活动
- 哪些是明确机会
- 哪些只是背景信息
- 对下一个节点的输入建议

## 默认判断口径
- 高优先级：
  - 明确的 `region theme`
  - 明确的 `competition / thematic competition`
  - 与当前时间窗口接近的活动
- 中优先级：
  - 明确的平台规则更新
- 低优先级：
  - 一般教学、背景宣传、非当前周期机会

## 命令示例
```bat
run.bat "U:\Project\MainCode\3.Work\WQB\wqb_cli\docs\research_runs\2026-05-06_restart_workflow"
```
