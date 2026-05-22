# F 数据与字段可行性

## 目标

基于 D 的主塔，使用 `data_all`、平台 data API、以及当前账户已有 ACTIVE REGULAR alpha，产出可用 datafield 库。

F 负责两件事：
- 找候选字段。
- 找目标塔下已经用过的 alpha/datafield，并把这些字段加入硬排除或强降权。

## 输入

必要：
- D 的 `main_tower.json`，至少包含 `region`、`delay`、`category` 或目标塔名，例如 `CHN/D1/PV`。
- `wqb_cli/local/data_all/info_data.bin`。
- `wqb_cli/local/data_all/all_data.pickle`。

可选：
- 历史已使用 datafield 列表。
- K 回退时的字段弱点诊断。

## 只允许的 CLI

候选字段与历史表现：

```powershell
wqb scope files
wqb scope list
wqb scope show <REGION_DELAY> --output <node_dir>/scope_summary.json
wqb scope top <REGION_DELAY> --group datafield --min-count 5 --limit 100 --output <node_dir>/top_datafields.json
wqb scope alpha-rows <REGION_DELAY> --table os --datafield <field> --limit 20 --columns id,sharpe,fitness,turnover,margin --output <node_dir>/field_os_rows.json
wqb data fields --output <node_dir>/platform_fields.json
wqb data datasets --output <node_dir>/platform_datasets.json
```

目标塔下已有 ACTIVE REGULAR alpha，优先尝试 tag 精确筛选：

```powershell
wqb alpha list `
  --type REGULAR `
  --settings-region <REGION> `
  --settings-delay <DELAY> `
  --settings-instrument-type EQUITY `
  --limit 100 `
  --order=-dateSubmitted `
  --status ACTIVE `
  --tag "<REGION>/D<DELAY>/<CATEGORY_UPPER>" `
  --output <node_dir>/active_regular_alphas__<REGION>_D<DELAY>_<CATEGORY_UPPER>__tag.json
```

例如 `CHN/D1/PV`：

```powershell
wqb alpha list `
  --type REGULAR `
  --settings-region CHN `
  --settings-delay 1 `
  --settings-instrument-type EQUITY `
  --limit 100 `
  --order=-dateSubmitted `
  --status ACTIVE `
  --tag "CHN/D1/PV" `
  --output <node_dir>/active_regular_alphas__CHN_D1_PV__tag.json
```

如果 tag 结果非空，优先使用 tag 结果提取已用 alpha 和 datafields。

如果 tag 结果为空、tag 未维护、或结果与 `pyramids[].name` 不一致，再退回目标 region/delay 全量自查：

```powershell
wqb alpha list `
  --type REGULAR `
  --settings-region <REGION> `
  --settings-delay <DELAY> `
  --settings-instrument-type EQUITY `
  --limit 100 `
  --order=-dateSubmitted `
  --status ACTIVE `
  --output <node_dir>/active_regular_alphas__<REGION>_D<DELAY>.json
```

任一查询如果返回 `count > 100`，必须继续用 `--offset 100`、`--offset 200` 翻页，直到 `next = null` 或覆盖全部结果。

不要使用下面这种写法作为有效过滤条件：

```powershell
wqb alpha list ... --param pyramid=pv
```

实测 `/users/self/alphas?pyramid=pv` 会返回 `200 OK`，但不会过滤结果；乱值也返回同样结果。

## 本地处理规则

1. 从 `active_regular_alphas__*.json` 的 `response.body.results` 读取 alpha 列表。
2. 目标塔优先用 `pyramids[].name` 精确匹配，例如 `CHN/D1/PV`。
3. 如果某条 alpha 没有 `pyramids`，再用 `category` 辅助判断，例如 `PRICE_VOLUME` 对应 PV。
4. 对筛出的目标塔 alpha，读取 `regular.code`。
5. FASTEXPR alpha 从表达式 token 中提取 datafield。
6. PYTHON alpha 优先从 `@alpha(data=[...])` 中提取 datafield。
7. `close`、`open`、`high`、`low`、`volume`、`returns` 等基础价量字段也要记录，但和平台 datafield 分开标注。

## 输出

必要：
- `active_regular_alphas__<REGION>_D<DELAY>_<CATEGORY_UPPER>__tag.json`：tag 精确查询原始结果，如果 tag 可用则必须输出。
- `active_regular_alphas__<REGION>_D<DELAY>.json`：region/delay 全量自查原始结果，在 tag 不可用、为空或不一致时必须输出。
- `target_tower_active_alphas.json`：本地筛出的目标塔 alpha，至少包含 `id`、`status`、`dateSubmitted`、`category`、`pyramids`。
- `used_datafields_by_tower.json`：目标塔已用字段，至少包含字段名、来源 alpha id、出现次数、是否基础价量字段。
- `candidate_datafields.json`：候选字段库。
- `banned_datafields.json`：硬排除字段，必须包含已使用字段和 OS 差字段。
- `preferred_datasets.json`：可优先使用的数据集。
- `field_screening_rationale.md`
- `node_summary.md`

可选：
- `scope_summary.json`
- `top_datafields.json`
- `field_os_rows__*.json`

## 筛选优先级

1. OS 效果差的数据不用。
2. 目标塔已使用 datafield 硬排除。
3. 已使用 dataset 尽量不用。

## 成功条件

- 输出可直接供 H/I 选择的候选 datafield 库。
- 明确说明服务端没有使用 `pyramid` filter。
- 明确说明是否使用了 tag 精确结果；如果没用，写明退回全量自查的原因。
- 明确列出目标塔已有 ACTIVE REGULAR alpha。
- 明确列出目标塔已使用 datafields。
- 每个候选字段都有保留理由和主要风险。

## 下一路

- `G 社区与文档经验`
- `H 经济学机制假设`
