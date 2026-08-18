# E 字段类型与单位契约

## 目标

逐字段验证 live metadata、数据类型、单位、缺失编码、更新频率、VECTOR reducer 和 Group 输入资格，避免把命名猜测带入大批量回测。

## 输入

- D 的 `field_sampling_frame.json`
- C 的 `simulation_settings.json`

## 推荐命令

```cmd
wqb data field <field_id> --output <node_dir>\field_meta__<field_id>.json
wqb data operators --output <node_dir>\operators.json
wqb sim options --output <node_dir>\simulation_options.json
```

## 输出

- `field_contracts.json`
- `vector_reducer_contracts.json`
- `group_input_contracts.json`
- `missing_value_contracts.json`
- `rejected_fields.json`
- `operator_inventory.json`
- `commands.md`
- `node_summary.md`

每条 `field_contracts.json` 至少包含：`field_id`、`dataset_id`、`data_type`、`unit`、`coverage`、`update_cadence`、`missing_encoding`、`allowed_roles`、`required_preprocessor`、`source_ref` 和 `verification_status`。

## 硬规则

- VECTOR 字段必须绑定平台支持的 reducer，未 reduction 不得进入 H。
- 只有 live contract 明确确认的 Group 值才能进入 group operator；整数代码、名称含 industry 的字段或普通 `Unit[]` 都不能被猜成 Group。
- 单位不明、类型冲突或缺失编码不明的字段直接拒绝，不把验证成本推迟到 J。
- E 不写 expression，不定义 template family。

## 成功条件

- 所有进入 H 的字段都有可机器读取的完整契约。
- operator inventory 与 C 的 region/delay/language 一致。

## 下一跳

- `F 分层抽样设计`
