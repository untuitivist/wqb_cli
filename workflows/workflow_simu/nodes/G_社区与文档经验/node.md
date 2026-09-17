# G 证据包与结构约束

## 目标

G 围绕当前 tower 与 F 候选字段建立可追溯证据包，并提炼 H 可以检验的机制线索、I 必须遵守的结构约束和 K 需要观察的失效模式。

G 不直接生成表达式，不决定 simulation settings，也不以社区点赞数替代机制证据。

## 输入

必要：
- D 的 `main_tower.json`
- F 的 `candidate_datafields.json`
- `wqb_cli/local/community/community.sqlite3`

可选：
- 用户提供的帖子、论坛链接、平台页面、论文或研报线索
- `wqb_cli/local/evidence/costs/wind.jsonl`：已有 Wind 积分校准账本

## 硬要求

G 必须同时完成以下四类搜索，缺任何一类都不能算完成：

1. 本地社区库搜索
2. 官方文档搜索
3. 平台资料搜索
4. 相关论文或研报搜索

每条进入结论的证据必须记录 `source_type`、原始路径或 URL、查询词、抓取时间、支持的字段/机制以及证据局限。无法取得正文的搜索摘要只能标为线索。

### Wind reality evidence

Wind 是 G 的**结构化现实观察源**，不是第五类必须无条件调用的搜索源。只有当前研究满足以下条件时才启用：

- F 已完成最终 freeze：`candidate_datafields.json` 明确 `freeze_status=FROZEN`、`complete=true`、`scope_pending=false`；
- 候选已经按经济机制收敛成 3–6 个 pre-Wind `mechanism_families.json`，不再是逐字段盲查；
- D main tower、F candidates、BRAIN field metadata snapshots、pre-Wind evidence 与 run constraints 已生成并验证 `research_freeze.json`；
- 当前 tower/字段涉及 Wind 能提供现实观察的财务、估值、分析师、公司事件、基金、债券、指数或宏观机制；
- 已有对应 `server_type.tool_name` 的积分 p95 校准记录；
- 已记录 fresh Alice Market balance，且 `wqb evidence wind plan-check` 通过当前可用积分预算门。

默认研究计划最多 **6 个机制**，每个机制最多 **3 次 Wind 调用**。不得对 `candidate_datafields.json` 做 `for field -> query Wind` 的逐字段扩散。

Wind 查询必须通过 `wqb evidence wind plan-check` + `wqb evidence wind execute-plan` 执行。`wqb evidence wind call ...` 在 workflow 中 fail closed；也禁止节点直接绕过 Evidence Provider 调 `node scripts/cli.mjs`，否则会绕过 freeze、预算、provider contract lock 与 no-blind-replay journal。

## 搜索顺序

1. 读取 F 最终冻结的候选字段及字段描述
2. 为每个字段提炼机制关键词并把字段聚成 3–6 个 `mechanism_families.json`；每个 family 只允许引用 F fields
3. 读取/保存所有 frozen candidate 的 BRAIN field metadata snapshots
4. 先做本地社区库搜索
5. 再做官方文档与平台资料搜索
6. 最后做论文与研报搜索
7. 用 D/F/mechanism families/BRAIN snapshots/pre-Wind evidence/run constraints 生成并验证 `research_freeze.json`
8. 对需要现实验证的承重机制生成只引用 frozen mechanism ids 的 `wind_reality_plan.json`
9. 把当前 Alice Market 账户余额记录为 `wqb evidence balance add wind ...`，再用该 fresh balance 和本地 p95 profile 运行预算门；通过后才执行 Wind reality checks
10. 对相互矛盾的结论保留冲突记录
11. 汇总得到机制线索、结构约束、禁忌和适用边界

## 论文搜索优先级

- 先检查环境里是否存在 `arxiv_cli`
- 如果存在，必须优先使用 `python -m arxiv_cli ...`
- 只有 `arxiv_cli` 不可用、报错或没有有效结果时，才允许退回其他论文搜索工具

## 推荐 CLI

```powershell
# 社区搜索
wqb community search "volume" --limit 20 --output <node_dir>/community_search__volume.json
wqb community search "price" --limit 20 --output <node_dir>/community_search__price.json
wqb community search "technical" --limit 20 --output <node_dir>/community_search__technical.json

# 官方文档
wqb docs list --output <node_dir>/docs_list.json
wqb docs show "simulations" --output <node_dir>/docs__simulations.md
wqb docs show "alpha_submission" --output <node_dir>/docs__alpha_submission.md

# 平台资料搜索
wqb search "volume" --output <node_dir>/platform_search__volume.json
wqb search "price" --output <node_dir>/platform_search__price.json
wqb search "momentum" --output <node_dir>/platform_search__momentum.json

# arxiv-cli 基础检查
arxiv --help
arxiv search --help
arxiv search query --help

# arxiv-cli - 简单 AND 查询（search query）
arxiv search query --all "volume" --all "price" --category q-fin.ST --max-results 10 --sort-by relevance --output <node_dir>/arxiv__volume_price.json
arxiv search query --all "momentum" --category q-fin.ST --max-results 10 --sort-by relevance --output <node_dir>/arxiv__momentum.json
arxiv search query --all "volatility" --category q-fin.ST --max-results 10 --sort-by relevance --output <node_dir>/arxiv__volatility.json

# arxiv-cli - 复杂 OR 查询（search raw）
arxiv search raw "cat:q-fin.ST AND (all:\"volume price\" OR all:\"technical indicator\" OR all:\"trading factor\")" --max-results 10 --sort-by relevance --output <node_dir>/arxiv__quant_factors.json

# Wind provider readiness
wqb evidence wind status --output <node_dir>/wind_status.json
wqb evidence cost profile --output <node_dir>/wind_cost_profile.json

# 在任何 Wind treatment 前冻结 paired split；每个 F candidate 都必须有 BRAIN metadata snapshot
wqb evidence experiment freeze `
  --run-id <RUN_ID> `
  --main-tower <D_node_dir>/main_tower.json `
  --candidate-datafields <F_node_dir>/candidate_datafields.json `
  --mechanisms <node_dir>/mechanism_families.json `
  --run-constraints <run_dir>/run_constraints.json `
  --brain-field-snapshot <node_dir>/field_meta__field_a.json `
  --non-wind-evidence <node_dir>/evidence_index.json `
  --output <run_dir>/research_freeze.json
wqb evidence experiment freeze-verify --input <run_dir>/research_freeze.json

# 记录真实余额；execute-plan 不接受 inline balance 代替这个 ledger observation
wqb evidence balance add wind --available-points <真实余额> --source alice_market_account

# 对已经收敛且已冻结的 reality plan 做预算/standing/freeze 检查
wqb evidence wind plan-check --input <node_dir>/wind_reality_plan.json --output <node_dir>/wind_plan_check.json

# 预算门通过后执行整个已批准 plan；内部串行、journal、可恢复
wqb evidence wind execute-plan `
  --input <node_dir>/wind_reality_plan.json `
  --output <node_dir>/reality_evidence_index.json
```

## Wind reality plan contract

`wind_reality_plan.json` 至少包含：

```json
{
  "run_id": "<RUN_ID>",
  "freeze_manifest": "<run_dir>/research_freeze.json",
  "balance_max_age_seconds": 1800,
  "checks": [
    {
      "mechanism_id": "<mechanism_id>",
      "node": "G",
      "purpose": "research",
      "server_type": "stock_data",
      "tool_name": "get_stock_fundamentals"
    }
  ]
}
```

运行前必须用 `wqb evidence balance add wind --available-points <真实余额>` 记录 Alice Market 的真实账户读数；plan 可省略 `available_points` 并读取最近一次 fresh balance。不得把“每日赠送 1000”当永恒常量写死。

## 输出

必要：
- `evidence_index.json`
- `query_log.md`
- `community_lessons.md`
- `official_docs_lessons.md`
- `platform_materials_lessons.md`
- `paper_research_lessons.md`
- `field_usage_warnings.md`
- `structure_constraints.md`
- `node_summary.md`

当 Wind reality evidence 被启用时额外必要：
- `mechanism_families.json`
- `field_meta__*.json`（覆盖所有 frozen F candidates）
- `research_freeze.json`
- `wind_status.json`
- `wind_cost_profile.json`
- `wind_reality_plan.json`
- `wind_plan_check.json`
- `reality_evidence_index.json`

## 成功条件

- 四类资料都有实际搜索证据文件
- 明确区分哪些结论来自社区经验、官方文档、平台资料、论文或研报
- `evidence_index.json` 中每条结论都能追溯到原始证据
- 明确列出未证实、冲突和不可外推的结论
- 输出能够支持 H 建立机制契约，但不包含可直接回测的 expression 列表
- 如果启用了 Wind，则每条 Wind 结论都引用可验证 `EvidenceRecord.evidence_id`，并保留 provider contract fingerprint、raw hash、warnings 与 limitations
- 如果 Wind 因 runtime/key/quota/budget gate 不可用，不得伪造 reality evidence；必须在 `node_summary.md` 明确其未完成 standing

## 下一跳

- `H 可检验机制契约`
