# I 候选生成与 manifest

## 目标

按 F 的固定 seed 和配额，从 H 定义的每个有效 family population 中无放回抽样，解析所有 placeholder，并生成符合 `template_contract.md`、具有完整 lineage 和唯一计算身份的 manifest。

I 只生成和校验，不发送任何 simulation 请求。

## 输入

- C 的 `simulation_settings.json` 与 `settings_identity.json`
- E 的 field/operator contracts
- F 的 allocation/randomization/analysis contracts
- H 的 component catalog、family specs 和 population estimates

## 推荐命令

```cmd
wqb data operators --output <node_dir>\operators_live.json
wqb sim options --output <node_dir>\simulation_options_live.json
wqb sqlitesimu template-validate <node_dir>\simulation_manifest.json --output <node_dir>\template_validation.json
```

## 输出

- `template_families.json`
- `component_catalog.json`
- `expression_candidates.json`
- `simulation_manifest.json`
- `validation_report.json`
- `template_validation.json`
- `candidate_identity_index.json`
- `operator_constraints_check.md`
- `commands.md`
- `node_summary.md`

## Candidate lineage

每个 candidate 的 `metadata` 至少包含：

- `workflow_run_id`
- `template_family_id`、`template_version`、`template_epoch`、中英文模板名、中文逻辑、`family_ordinal` 和 `family_draw_index`
- `mechanism_id`、`component_ids`、字段 id 与字段角色
- 完整参数选择、rng seed、population ordinal
- canonical expression、完整 expression hash、去 header 的 calculation hash、settings hash
- operator count、unique field count、evidence refs
- `single_mechanism = true`

`simulation_manifest.json` 的 `metadata` 必须保留这些字段，使 SQLite experiment 能按 family、component、dataset 和参数回溯。

## 机器校验

J 之前必须全部通过：

- 实际 family 数和每族配额等于 F 计划，census 例外有记录。
- expression 全局唯一，完整 payload fingerprint 全局唯一。
- expression 不含未解析 placeholder，且保留模板两行 header、变量赋值和最终 `template_LLM` 行。
- `calculation_hash + settings_hash` 在当前 manifest、parent run 和已登记历史中唯一。
- 没有 exact sign twin、可交换重复、反向 antisymmetric duplicate 或 canonical-equivalent AST。
- 每个 operator 存在于 live inventory，参数和窗口合法。
- 每个 field、VECTOR reducer、Group input 和 unit 与 E 契约一致。
- settings region 与 C 冻结值一致；I 不重新评价或改写 C 的选区决定。
- 所有 candidate 使用同一个 settings hash。
- family population 未被有放回采样，未用 wrapper-only 变体补足数量。
- manifest candidate 数等于 identity index 数，lineage 无空值。

## Manifest 约束

- `run.name`、`run.enrichment_profile`、顶层 metadata 和 candidates 完整。
- `run.enrichment_profile` 至少支持 alpha detail 与 PnL enrichment。
- 每个 candidate 使用 `expression + settings` 或完整 `payload`，不得依赖 J 补默认值。
- 不包含 alpha submit、patch 或 tag 动作。

## 成功条件

- `validation_report.json.verdict = true`，且 `template_validation.json` 的 `ok/verdict = true`、violation count 为 0。
- 总数由 family allocation 得出，不为达到任意整数而填充。
- manifest 可直接由 J 入库，J 无需修改 expression、metadata 或 settings。

## 下一跳

- `J SQLite 入库、启动与交接`
