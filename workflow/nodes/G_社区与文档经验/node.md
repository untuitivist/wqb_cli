# G 社区与文档经验

## 目标

基于 D 和 F，检索本地社区库、官方文档和平台资料，提取与主塔和候选字段相关的经验。

## 输入

必要：

- D 的 `main_tower.json`。
- F 的 `candidate_datafields.json`。
- `wqb_cli/local/community/community.sqlite3`。

可选：

- 用户提供的帖子、论文或材料。

## 只允许的 CLI

```powershell
wqb community stats --output <node_dir>/community_stats.json
wqb community search <keyword> --limit 20 --output <node_dir>/community_search__keyword.json
wqb docs list --output <node_dir>/docs_list.json
wqb docs show simulations/create/README.md --output <node_dir>/docs_sim_create.md
wqb consultant faqs --output <node_dir>/consultant_faqs.json
wqb consultant osmosis-guide --output <node_dir>/osmosis_guide.json
wqb consultant visualization-tool --output <node_dir>/visualization_tool.json
```

## 输出

必要：

- `community_lessons.md`
- `platform_docs_lessons.md`
- `field_usage_warnings.md`
- `node_summary.md`

可选：

- `community_search__*.json`
- `docs_*.md`

## 成功条件

- 产出能影响 H/I/J/K 的经验规则，而不是简单摘录。
- 明确哪些社区结论只是经验、哪些来自官方文档。

## 下一跳

- `H 经济学机制假设`
