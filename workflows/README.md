# WQB Research Workflows

本目录维护两套相互独立的研究流程。顶层文档只负责说明如何选择流程；任何运行产物、节点输入、数据库或控制流都不得在两套流程之间共享。

## 目录

```text
workflows/
  workflow_simu/          小规模、自适应的原研究流程
  workflow_batchsimu/     模板族筛选与批量回测流程
```

## 流程边界

`workflow_simu`：

- 目标是验证少量具体机制或表达式；
- 每轮候选规模有明确上限，结果会立即影响下一轮表达式；
- agent 需要阅读单个 alpha 的 visualization、check、PnL 和相关性；
- 使用自己的 A-M 节点、run 目录和产物契约；
- 最终可能进入提交节点 M。

`workflow_batchsimu`：

- 目标是比较多个参数化模板族，而不是寻找某一条 alpha；
- 首轮需要用固定设置估计每个模板族的有效结果密度；
- 表达式一次性写入 manifest，随后由 `wqb sqlitesimu` 独立提交、轮询、重登和入库；
- agent 不参与逐条回测，只在 run 终态后读取 SQLite/export 做聚合分析；
- 使用自己的 A-M 节点、run 目录、SQLite 数据库和产物契约；
- K 在终态后分析与选候选，L 完成慢速终检，M 是唯一允许执行 Alpha submit 的节点；累计目标未完成时只能从本流程 A 创建新的独立 batch。

候选数量不是唯一判断标准。即使只有几百条，只要研究问题是“哪个模板族更有效”，也必须使用 `workflow_batchsimu`。

## 物理隔离

```text
research_runs/
  workflow_simu/
    run_{YYYYMMDD_HHMMSS}_{agent_name}/
  workflow_batchsimu/
    run_{YYYYMMDD_HHMMSS}_{agent_name}/
```

每个 run 必须从所属目录的 A 节点开始，并创建自己的 `run_manifest.json`。至少包含：

- `workflow_type`: `workflow_simu` 或 `workflow_batchsimu`
- `started_at`
- `target_tower`
- `alpha_submission_allowed`
- `source_workflow_graph`

每个节点只写自己的目录，并保存 `commands.md`、原始证据和 `node_summary.md`。两套流程即使研究同一 tower，也必须重新完成自己的 A-F，不得读取另一套流程的节点目录。batch SQLite 只能位于对应 batch run 的 J 目录；simu 节点不得打开它。

## 禁止事项

- 不得用 `workflow_simu/J` 人工循环提交模板族大批次。
- 不得在 `workflow_batchsimu/J` 期间让 agent 逐条读取或修补实验。
- 不得从任一流程跳转、回退或 handoff 到另一流程。
- 不得把另一流程的节点产物声明为本流程必要输入。
- 不得把表达式唯一、operator 结构不同当作低相关性的证据。
- 不得在 batch run 非终态时计算模板族通过率或决定扩展。
- 不得把诊断 run、canary run 与权威 batch run 混合统计。
