# F 数据与字段可行性

## 目标

基于 D 的主塔，使用 `data_all` 和平台 data API 产出可选 datafield 库。

## 输入

必要：

- D 的 `main_tower.json`。
- `wqb_cli/local/data_all/info_data.bin`。
- `wqb_cli/local/data_all/all_data.pickle`。

可选：

- 历史已使用 datafield 列表。
- K 回退时的字段弱点诊断。

## 只允许的 CLI

```powershell
wqb scope files
wqb scope list
wqb scope show <REGION_DELAY> --output <node_dir>/scope_summary.json
wqb scope top <REGION_DELAY> --group datafield --min-count 5 --limit 100 --output <node_dir>/top_datafields.json
wqb scope alpha-rows <REGION_DELAY> --table os --datafield <field> --limit 20 --columns id,sharpe,fitness,turnover,margin --output <node_dir>/field_os_rows.json
wqb data fields --output <node_dir>/platform_fields.json
wqb data datasets --output <node_dir>/platform_datasets.json
```

## 输出

必要：

- `candidate_datafields.json`：候选字段库。
- `banned_datafields.json`：硬排除字段，包含已使用字段和 OS 差字段。
- `preferred_datasets.json`：可优先使用的数据集。
- `field_screening_rationale.md`
- `node_summary.md`

可选：

- `scope_summary.json`
- `top_datafields.json`
- `field_os_rows__*.json`

## 筛选优先级

1. OS 效果差的数据不用。
2. 已使用 datafield 硬排除。
3. 已使用 dataset 尽量不用。

## 成功条件

- 输出可直接供 H/I 选择的候选 datafield 库。
- 每个候选字段都有保留理由和主要风险。

## 下一跳

- `G 社区与文档经验`
- `H 经济学机制假设`
