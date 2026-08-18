# C 目标与设置冻结

## 目标

独立选择本 batch run 的 target tower，并冻结唯一 simulation settings cell，使后续差异主要来自模板族、组件和参数，而不是设置漂移。

## 输入

- B 的 `batch_objective.json`
- B 的 `quality_gates.json`

## 推荐命令

```cmd
wqb user consultant-summary --output <node_dir>\consultant_summary.json
wqb user pyramid-alphas --start-date <quarter_start> --end-date <quarter_end> --output <node_dir>\quarter_pyramid_alphas.json
wqb user pyramid-multipliers --start-date <quarter_start> --end-date <quarter_end> --output <node_dir>\quarter_pyramid_multipliers.json
wqb data categories --output <node_dir>\data_categories.json
wqb sim options --output <node_dir>\simulation_options.json
```

## 输出

- `target_context.json`：region、delay、category、tower 状态及选择依据。
- `simulation_settings.json`：完整、可直接放入 manifest 的 settings。
- `settings_identity.json`：canonical JSON 和 SHA-256 settings hash。
- `settings_rationale.md`
- `commands.md`
- `node_summary.md`

## 硬规则

- 一个权威 run 只有一个 settings hash。
- 新 run 的 region 不得为 `CHN` 或 `USA`；从 `wqb sim options` 返回的其余可用 region 中选择，不硬编码未经平台确认的 allowlist。
- region 选择必须比较目标 tower、倍率或机会、数据覆盖与研究拥挤度，并在 `settings_rationale.md` 记录证据；不得仅沿用上一次 run。
- region、delay、universe、instrumentType、language、decay、neutralization、truncation、pasteurization、unitHandling、nanHandling、visualization 和 testPeriod 必须显式记录。
- 本节点不读取提交额度，也不授权提交 Alpha。
- 若目标是比较 settings，必须把每个 settings cell 作为不同 run，而不是在一个 manifest 中混合。

## 成功条件

- settings 全部来自平台支持值，并与目标 tower 一致。
- `simulation_settings.json.region` 不属于 `CHN / USA`，且 I 的 `template-validate` 再次通过机器闸门。
- 后续节点不再修改 settings；任何修改都使当前 run 作废并重新从 C 开始。

## 下一跳

- `D 字段宇宙快照`
