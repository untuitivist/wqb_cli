# B_主题_平台机会

## Role
- 采集当前平台最近的主题、活动、消息摘要。
- 为主塔选择和后续机制判断提供平台机会背景。

## Upstream
- `A_登录_共享认证态`

## Downstream
- `D_选主塔`
- `H_经济学机制假设`

## Inputs
### Necessary
- `A` 已建立的共享认证态

### Optional
- 本轮 run 根目录

## Outputs
### Necessary
- `01_theme/messages_summary.json`
- `01_theme/messages_full.json`
- `01_theme/events.json`
- `01_theme/node_summary.md`

### Optional
- 主题优先级判断备注
- 值得关注的比赛/地区/主题标题摘录

## Success Criteria
- 成功拿到最近消息、完整消息和活动列表。
- 能从中提炼出后续主塔选择和机制判断可用的主题背景。

## Failure Criteria
- 消息和活动数据缺失。
- 无法形成可用的平台机会背景。
