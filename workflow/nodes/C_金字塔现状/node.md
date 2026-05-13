# C\_金字塔现状

## Role

- 读取季度金字塔、全部金字塔、金字塔乘数。
- 为主塔选择提供点塔优先级、竖向成熟度和 multiplier 信息。

## Upstream

- `A_登录_共享认证态`

## Downstream

- `D_选主塔`

## Inputs

### Necessary

- `A` 已建立的共享认证态

### Optional

- 本轮 run 根目录

## Outputs

### Necessary

- `02_pyramid/current_quarter_pyramids.json`
- `02_pyramid/all_pyramids.json`
- `02_pyramid/multipliers.json`
- `02_pyramid/node_summary.md`

### Optional

- 关键竖向塔统计摘录
- category 占比判断备注

## Success Criteria

- 三类金字塔数据均可用。
- 能据此判断：
  - 哪些塔接近点亮 (优先级最高)
  - 哪些竖向塔成熟 (在没有塔接近点亮时作为判断依据)
  - 哪些 multiplier 更高 (优先级最低, 约不考虑)

## Failure Criteria

- 缺少季度、全量或 multiplier 任一关键数据。

