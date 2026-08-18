# D 字段宇宙快照

## 目标

在 C 的固定 target/settings 下，建立带 provenance 的字段与 dataset 候选宇宙，并独立识别该 tower 已用字段、低质量字段和 dataset 集中风险。

## 输入

- C 的 `target_context.json`
- C 的 `simulation_settings.json`
- 本地 `data_all`（存在时）

## 推荐命令

```cmd
wqb scope files
wqb scope show <REGION_DELAY> --output <node_dir>\scope_summary.json
wqb scope top <REGION_DELAY> --group datafield --min-count 5 --limit 200 --output <node_dir>\top_datafields.json
wqb scope top <REGION_DELAY> --group dataset --min-count 5 --limit 100 --output <node_dir>\top_datasets.json
wqb data datasets --region <REGION> --delay <DELAY> --limit 100 --output <node_dir>\platform_datasets.json
wqb data fields --region <REGION> --delay <DELAY> --limit 100 --output <node_dir>\platform_fields_page1.json
wqb alpha list --type REGULAR --settings-region <REGION> --settings-delay <DELAY> --status ACTIVE --limit 100 --output <node_dir>\active_regular_alphas_page1.json
```

所有分页接口必须翻页到 `next = null`。目标 tower 优先按 `pyramids[].name` 精确匹配，tag 只能作为可验证的加速路径。

## 输出

- `field_universe.json`：字段 id、dataset、category、coverage、usage、来源和抓取时间。
- `dataset_universe.json`
- `target_tower_active_alphas.json`
- `used_datafields_by_tower.json`
- `excluded_fields.json`
- `dataset_caps.json`
- `field_sampling_frame.json`
- `commands.md`
- `node_summary.md`

## 筛选原则

- OS 明显差、字段描述空泛或覆盖不足的字段排除。
- 已在目标 tower 使用的字段排除或按 B 预先声明的规则强降权。
- dataset 配额在抽样前固定，防止一个大 dataset 淹没其他机制。
- 字段池只在 D 冻结；后续节点不得临时加入字段。

## 成功条件

- 每个进入 E 的字段都能追溯到原始平台或本地数据记录。
- 字段宇宙、排除理由和 dataset cap 可复现。

## 下一跳

- `E 字段类型与单位契约`
