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

## 硬要求

G 必须同时完成以下四类搜索，缺任何一类都不能算完成：

1. 本地社区库搜索
2. 官方文档搜索
3. 平台资料搜索
4. 相关论文或研报搜索

每条进入结论的证据必须记录 `source_type`、原始路径或 URL、查询词、抓取时间、支持的字段/机制以及证据局限。无法取得正文的搜索摘要只能标为线索。

## 搜索顺序

1. 读取 F 给出的候选字段及字段描述
2. 为每个字段提炼机制关键词
3. 先做本地社区库搜索
4. 再做官方文档与平台资料搜索
5. 最后做论文与研报搜索
6. 对相互矛盾的结论保留冲突记录
7. 汇总得到机制线索、结构约束、禁忌和适用边界

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

# arxiv-cli - dry-run 预览（先看查询是否构造正确）
arxiv search query --all "volume" --all "price" --category q-fin.ST --dry-run
arxiv search raw "cat:q-fin.ST AND (all:\"volume price\" OR all:\"technical indicator\")" --dry-run

# arxiv-cli - 文本格式快速预览
arxiv search raw "cat:q-fin.ST AND (all:\"volume price\" OR all:\"technical indicator\")" --max-results 5 --format text
```

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

可选：
- `community_search__*.json`
- `docs__*.md`
- `platform_search__*.json`
- `arxiv__*.json`

## 成功条件

- 四类资料都有实际搜索证据文件
- 明确区分哪些结论来自社区经验、官方文档、平台资料、论文或研报
- `evidence_index.json` 中每条结论都能追溯到原始证据
- 明确列出未证实、冲突和不可外推的结论
- 输出能够支持 H 建立机制契约，但不包含可直接回测的 expression 列表

## 下一跳

- `H 可检验机制契约`
