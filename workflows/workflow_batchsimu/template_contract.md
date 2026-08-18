# BatchSimu 模板与分析格式契约

本文件是 `workflow_batchsimu` 内部的唯一格式基线。H 产出参数化模板，I 产出已实例化 candidate，K 从权威 run export 生成固定分析报告。三者不得用自然语言约定代替机器字段。

## H：模板定义格式

`template_catalog.md` 中每个模板严格使用以下人读格式：

````text
1. [English Template Name] - 中文模板名
逻辑: 一句话说明数据、变化或关系为何可能形成收益机制，以及预期失效条件。
模板:
```text
# [English Template Name]
# [YYYYMMDD] - [version/context] - [epoch N]
signal_matrix_variable = vec_avg({vector_datafield_signal});
state_variable = {time_series_operator_state}(signal_matrix_variable, {state_window});
template_LLM = group_neutralize(state_variable, {group_datafield_peer});
template_LLM
```
````

模板 placeholder 只能使用以下可解析命名：

- `{<type>_datafield_<role>}`：字段类型与经济角色，例如 `{vector_datafield_signal}`。
- `{<meaning>_window}`：有约束的整数窗口，例如 `{state_window}`。
- `{<category>_operator_<meaning>}`：来自 live inventory 的 operator，例如 `{time_series_operator_state}`。
- `{constant_<name>}`：有单位和范围的常量，例如 `{constant_threshold}`。

模板正文必须满足：

- 第一行是英文模板名，第二行是日期、版本上下文和 epoch。
- 中间变量只赋值一次并以 `_variable` 结尾；最终赋值变量只能是 `template_LLM`。
- 每条赋值以分号结束，最后一个可执行行单独写 `template_LLM`。
- VECTOR 字段先按 E 的 reducer contract 转成 MATRIX；不得把 `Unit[]` 字段当 Group 输入。
- 每个 placeholder 都在 family spec 中声明 type、dimension、unit、domain、operator input/output 和组合约束。
- 一个 family 只表达一个收益机制。条件、peer comparison 和去噪可以增加结构，但不得拼接第二个独立 return signal。
- wrapper-only、exact sign twin、可交换重复、反对称反向重复和等价计算不得作为新模板。

## 版本与 epoch

- `template_family_id` 表示长期稳定的机制身份。
- `template_version` 在 AST skeleton、字段角色、operator contract 或参数 domain 改变时递增。
- `template_epoch` 表示同一版本的新实验波次。扩展只能使用新的 epoch 和此前未测试的 `calculation_hash`。
- 同一 authoritative run 只能包含一个 settings hash，并且同一 family/version 只能包含一个 epoch。
- `expression_hash` 覆盖含两行 header 的完整表达式；`calculation_hash` 只覆盖可执行正文，用于跨 epoch 防止重复计算。

## I：candidate 格式

I 必须解析全部 placeholder。可入库 expression 不允许残留 `{...}`，但必须保留模板的两行 header、变量赋值和最终 `template_LLM` 行。

每个 candidate metadata 至少包含：

```json
{
  "template_format_version": 1,
  "workflow_run_id": "run_...",
  "template_family_id": "family_...",
  "template_version": 1,
  "template_name": "English Template Name",
  "template_name_zh": "中文模板名",
  "template_logic_zh": "该模板的单一机制与失效条件。",
  "template_epoch": 1,
  "family_ordinal": 1,
  "family_draw_index": 1,
  "mechanism_id": "mechanism_...",
  "field_roles": {"field_id": "signal"},
  "parameters": {"state_window": 20},
  "rng_seed": 20260818,
  "population_ordinal": 1,
  "expression_hash": "sha256...",
  "calculation_hash": "sha256...",
  "settings_hash": "sha256...",
  "single_mechanism": true
}
```

`candidate_identity_index.json` 必须同时按完整 simulation payload fingerprint 和 `calculation_hash + settings_hash` 建索引。前者用于当前 manifest 去重，后者用于跨 version/epoch/run 排除已经计算过的等价正文。

J 前的强制命令：

```cmd
wqb sqlitesimu template-validate <i_node_dir>\simulation_manifest.json --output <i_node_dir>\template_validation.json
```

仅当退出码为 `0`、`ok = true`、`verdict = true` 且 `violation_count = 0` 时才能 enqueue。

## K：结果分析格式

K 只接受 `wqb sqlitesimu export` 生成的单个终态 run export。不得按创建时间抓取 alpha，不得混合其他 run，也不得依赖 notebook 的残留内存状态。

固定报告由以下命令生成：

```cmd
wqb sqlitesimu template-report <node_dir>\run_export.json --output <node_dir>\template_report.json --markdown-output <node_dir>\template_report.md
```

Markdown 的前三段名称和列式格式固定为：

1. `template alphas performance each template`：逐 template 的 Sharpe、Fitness、Turnover、Margin、Returns、Drawdown、PnL describe 统计。
2. `template alphas checks statistics`：逐 template/check 的 `FAIL / PASS / PENDING / WARNING / ERROR` 计数、value describe 和 limit values。
3. `template alphas best performance each metric`：逐 template 的 Sharpe/Fitness 代表，不跨 template 使用全局 fallback。

代表选择必须使用有符号最大值，禁止用绝对值把最差负 Sharpe 或负 Fitness 当成最佳值。先从该 template 内没有 `FAIL/ERROR` 的 READY alpha 选择；若该 template 没有这种 alpha，才在该 template 内 fallback，并显式标为 `all_ready_fallback`。

三段机器表之后，每个模板必须按以下格式给出描述，包含没有 READY 结果的模板：

```text
N. [English Template Name] - 中文模板名
逻辑: ...
实验成果评估: ...
关键发现: ...
改进方向: ...
```

该固定报告只完成格式化和基础完整性筛查。K 仍必须结合 F 的 denominator/Wilson contract、错误分类和真实 IS-PnL cluster 生成最终 `analysis_eligibility.json`；固定报告本身不能授权 L 扩展。

## 禁止降级

- 不使用无 seed 的随机抽样，不进行有放回补数。
- 不通过 alpha 创建时间推断 run 归属。
- 不把没有结果的模板从报告中静默删除。
- 不按单条最大 Sharpe 排模板，不用表达式外观代替实际 PnL correlation。
- 不把 `CANCELLED`、`BLOCKED` 或含 `SIMULATE_UNKNOWN` 的 run 用于扩展选择。
- 不在 K/L 修改 expression、manifest 或 J 的 SQLite。
