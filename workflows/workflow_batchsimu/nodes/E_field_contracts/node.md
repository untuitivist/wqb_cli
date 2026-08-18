# E 字段类型与单位契约

## 目标

逐字段验证 live metadata、数据类型、可取得的单位/缺失/更新信息、VECTOR reducer 和 Group 输入资格，避免把命名猜测带入大批量回测。平台接口没有返回某项 metadata 时必须显式记录缺口，不能伪造值。

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
- 类型冲突直接拒绝。单位、更新频率或缺失编码未由 live endpoint 暴露时，默认拒绝；唯一例外是 unary 字段或同 dataset、同量纲描述、显式定向的字段对，同时固定 `unitHandling = VERIFY`、`nanHandling = ON`，并将 contract 标为 `TYPE_CONFIRMED_SERVER_UNIT_VERIFY_REQUIRED`。该例外必须在 E 和 I validation 中可见，服务器确定性 unit 错误在 K 单列，不能归为平台故障。
- 不允许仅靠字段名猜测两个未知单位字段可加减；显式 pair contract 必须保存左右字段、描述和方向。
- E 不写 expression，不定义 template family。

## 成功条件

- 所有进入 H 的字段都有可机器读取的契约；endpoint 未暴露项必须使用明确 sentinel 和 verification mode，不能留空或声称已验证。
- operator inventory 与 C 的 region/delay/language 一致。

## 下一跳

- `F 分层抽样设计`
