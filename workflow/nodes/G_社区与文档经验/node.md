# G 社区与文档经验

## 目标

G 负责把当前 tower 与候选字段相关的资料搜全，并沉淀成后续 `H/I/K` 可直接使用的经验与约束。

## 输入

必要：
- D 的 `main_tower.json`
- F 的 `candidate_datafields.json`
- `wqb_cli/local/community/community.sqlite3`

可选：
- 用户提供的帖子、论文、研报、论坛链接

## 硬要求

G 必须同时完成以下四类搜索，缺任何一类都不能算完成：

1. 本地社区库
2. 官方文档
3. 平台资料
4. 相关论文/研报

## 论文搜索优先级

- 先检查环境里是否存在 `arxiv_cli`
- 若存在，必须优先使用 `python -m arxiv_cli ...`
- 只有 `arxiv_cli` 不可用、失败或无结果时，才允许退回其他工具

## 推荐 CLI

```powershell
wqb community search <keyword> --limit 20 --output <node_dir>/community_search__<keyword>.json
wqb docs list --output <node_dir>/docs_list.json
wqb docs show <doc_path> --output <node_dir>/docs__<doc_name>.md
wqb search <keyword> --output <node_dir>/platform_search__<keyword>.json
python -m arxiv_cli search query --all <keyword> --max-results 10 --sort-by relevance --output <node_dir>/arxiv__<keyword>.json
```

## 输出

必要：
- `community_lessons.md`
- `official_docs_lessons.md`
- `platform_materials_lessons.md`
- `paper_research_lessons.md`
- `field_usage_warnings.md`
- `node_summary.md`

可选：
- `community_search__*.json`
- `docs__*.md`
- `platform_search__*.json`
- `arxiv__*.json`

## 成功条件

- 四类资料均有实际搜索证据文件
- 明确区分哪些结论来自社区经验，哪些来自官方文档，哪些来自平台资料，哪些来自论文/研报
- 输出能直接支撑后续 H 的字段意义判断与 I 的结构选择

## 下一跳

- `H 经济学机制假设`
