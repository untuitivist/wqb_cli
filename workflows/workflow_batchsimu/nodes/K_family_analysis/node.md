# K 模板族批量分析

## 目标

仅在 J 的权威 run 终态后，基于同一 run 的 export 与 `simued_alpha_is_pnl` 完成运行完整性、错误分类、family density、质量分布和真实 IS-PnL 相关性聚类。

K 不生成 expression，不 enqueue，不恢复 worker，也不提交 Alpha。

## 输入

- B 的目标、quality gates 和 stop conditions
- F 的 allocation 与 analysis contracts
- I 的 family、candidate 和 identity artifacts
- J 的 `worker_handoff.json`、SQLite 和终态 status

## 推荐命令

```cmd
wqb sqlitesimu status <run_id> --db <j_node_dir>\simulations.sqlite3 --output <node_dir>\terminal_status.json
wqb sqlitesimu export <run_id> --db <j_node_dir>\simulations.sqlite3 --output <node_dir>\run_export.json
```

后续统计只读 `run_export.json`。不得对 J 的执行数据库写 SQL；不得把其他 run 的 export 合并进 denominator。

## 终态与完整性闸门

1. status 的 db 绝对路径和 run_id 必须与 J handoff 一致。
2. run state 必须是 `COMPLETED`、`COMPLETED_WITH_ERRORS`、`BLOCKED` 或 `CANCELLED`。
3. experiment 总数、family lineage、settings hash 和 manifest fingerprint 必须与 I/J 对齐。
4. `BLOCKED`、`CANCELLED`、`SUBMIT_UNKNOWN` 或 READY coverage 不足时，先把 run 标为 `analysis_ineligible`；不得据此选择扩展 family。
5. 诊断、canary、retired run 和不同 settings 的结果一律排除。

## 三层分析

### 1. Execution 与错误

按 family 报告 `READY / PERMANENT_FAILURE / SUBMIT_UNKNOWN / CANCELLED`。错误至少分为 authentication/throttle、platform transient、syntax/operator、data/unit、resource/time、unknown。认证和平台错误不能归因于 family 经济机制。

### 2. Density 与质量分布

严格使用 F 预注册口径计算 execution-ready rate、quality density 和 usable density，并报告 numerator、denominator、Wilson interval、Sharpe/fitness/turnover/margin 分位数和 checks 分布。不得只按 family 最大 Sharpe 排名。

### 3. IS-PnL 相关性

- 从 `simued_alpha_is_pnl` 读取每条 READY alpha 的 PnL 差分序列；兼容视图首项 `nan` 是预期行为。
- 按 F 预注册的缺失处理、最小重叠长度、correlation method 和 threshold 聚类。
- 相关性必须来自实际 PnL，不能从 expression 文本或 operator signature 推断。
- family shortlist 必须兼顾 density、质量和跨 cluster 覆盖；同一高相关 cluster 不得用多个代表虚增扩展名额。

## 输出

- `terminal_status.json`
- `run_export.json`
- `run_integrity.json`
- `experiment_state_counts.json`
- `error_taxonomy.json`
- `family_density.json`
- `quality_distributions.json`
- `pnl_correlation_clusters.json`
- `family_shortlist.json`
- `analysis_eligibility.json`
- `analysis_summary.md`
- `commands.md`
- `node_summary.md`

## 成功条件

- 每个 assigned candidate 在 state、错误、family 和 denominator 中恰好出现一次。
- 所有 family 比率都有原始计数和区间，不按小样本偶然值扩展。
- correlation cluster 可追溯到 alpha id、experiment id、family id 和 PnL source。
- 明确给出 run 是否具备 expansion 资格。

## 下一跳

- `L 扩展或终止`
