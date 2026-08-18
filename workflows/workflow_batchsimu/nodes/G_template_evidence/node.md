# G 模板群证据

## 目标

围绕 F 的实验设计和 E 的有效字段，建立模板群方法、字段机制、operator 语义和失效风险的可追溯证据包。G 只形成设计约束，不生成 expression。

## 输入

- B 的 `batch_objective.json`
- D 的 `field_sampling_frame.json`
- E 的 field/operator contracts
- F 的 `allocation_plan.json` 与 `analysis_contract.json`

## 必查来源

1. 本地社区全文与高票评论，至少覆盖“模板群”“模板”“alpha_func”“去重”“GEM”等关键词。
2. 官方 command documentation 和 simulation/operator 说明。
3. live platform 搜索结果与字段描述。
4. 与目标字段机制相关的论文或研报。

核心社区帖子应优先核对全文和作者评论，包括 `35253150989719`、`37285699644823`、`36770332492951`、`36530366174615`、`37289950228887`、`26054361848343`、`30725406640279`。帖子编号只作为检索入口，不能替代正文证据。

## 推荐命令

```cmd
wqb community stats --output <node_dir>\community_stats.json
wqb community search "模板群" --scope forum --limit 50 --output <node_dir>\community_template_group.json
wqb community search "模板" --scope forum --limit 50 --output <node_dir>\community_template.json
wqb community search "alpha_func" --scope forum --limit 50 --output <node_dir>\community_alpha_func.json
wqb community search "GEM" --scope forum --limit 50 --output <node_dir>\community_gem.json
wqb docs list --output <node_dir>\docs_list.json
wqb search template --output <node_dir>\platform_template_search.json
```

## 必须提炼的结论

- 模板群是可管理的参数化 family population，每个结果必须保留 `alpha_func` 等价 lineage。
- 初筛应对多个经济上不同的 family 等额随机抽样，社区案例约每族 80 条；扩展只集中到少数高密度且低冗余 family。
- 数据清理/reduction、核心经济关系、克制的 grouping 或 monotone detail 是不同层次，不能用 wrapper 替代核心关系。
- family 产量必须可计算，候选必须以完整 simulation identity 去重。
- factor density 是经验性筛选指标，不是结论；表达式结构也不能证明 PnL 低相关。
- 逐层追加 operator 并按同一批结果继续拟合存在过拟合风险，本流程不采用无上限 LEGO 式自适应堆叠。

## 输出

- `evidence_index.json`：source type、原始路径或 URL、查询词、抓取时间、支持结论和局限。
- `community_template_lessons.md`
- `official_operator_lessons.md`
- `platform_field_lessons.md`
- `mechanism_research_lessons.md`
- `family_design_constraints.json`
- `unsupported_patterns.json`
- `query_log.md`
- `commands.md`
- `node_summary.md`

## 成功条件

- 模板方法与字段机制证据分开记录，无法取得正文的摘要只标为 clue。
- 支持、反对和不确定证据都保留。
- H 可以据此定义 family，但 G 不包含可回测 expression 列表。

## 下一跳

- `H 机制组件与模板族`
