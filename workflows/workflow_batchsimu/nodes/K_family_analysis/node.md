# K 模板族批量分析与候选选择

## 目标

仅在 J 的权威 run 终态后，基于同一 run 的 export 与 `simued_alpha_is_pnl` 完成运行完整性、错误分类、family density、质量分布和真实 IS-PnL 相关性聚类。若 run 具备分析资格，再从不同 PnL cluster 中选择少量真实 Alpha 进入 L。

K 不生成 expression，不 enqueue，不恢复 worker，不执行慢速终检，也不提交 Alpha。

## 输入

- B 的目标、quality gates 和 stop conditions
- C 的提交额度快照和唯一 settings identity
- F 的 allocation 与 analysis contracts
- I 的 family、candidate 和 identity artifacts
- J 的 `worker_handoff.json`、SQLite 和终态 status

## 推荐命令

```cmd
wqb sqlitesimu status <run_id> --db <j_node_dir>\simulations.sqlite3 --output <node_dir>\terminal_status.json
wqb sqlitesimu export <run_id> --db <j_node_dir>\simulations.sqlite3 --output <node_dir>\run_export.json
wqb sqlitesimu template-report <node_dir>\run_export.json --minimum-ready-coverage <F_minimum_ready_coverage> --output <node_dir>\template_report.json --markdown-output <node_dir>\template_report.md
```

后续统计只读 `run_export.json`。不得按 alpha 创建时间补结果，不得对 J 的执行数据库写 SQL，不得把其他 run 的 export 合并进 denominator。

## 终态与完整性闸门

1. status 的 db 绝对路径和 run_id 必须与 J handoff 一致。
2. run state 必须是 `COMPLETED`、`COMPLETED_WITH_ERRORS`、`BLOCKED` 或 `CANCELLED`。
3. experiment 总数、family lineage、settings hash 和 manifest fingerprint 必须与 I/J 对齐。
4. `CANCELLED` 永远只能描述。`BLOCKED` 若仅由已隔离的 `SIMULATE_UNKNOWN` 引起，且 READY coverage 达到 F 预注册门槛，可分析 READY 子集；否则标记 `analysis_ineligible`。
5. 每个 `SIMULATE_UNKNOWN` 单独写入隔离清单，永远不自动重跑、不进入 PnL clustering、不选择、不提交；它不能连带否决同 run 已满足 coverage 合同的 READY Alpha。
6. 诊断、canary、retired run 和不同 settings 的结果一律排除。

## 三层分析

### 1. Execution 与错误

按 family 报告 `READY / PERMANENT_FAILURE / SIMULATE_UNKNOWN / CANCELLED`。错误至少分为 authentication/throttle、platform transient、syntax/operator、data/unit、resource/time、unknown。认证和平台错误不能归因于 family 经济机制。

### 2. Density 与质量分布

严格使用 F 预注册口径计算 execution-ready rate、quality density 和 usable density，并报告 numerator、denominator、Wilson interval、Sharpe/fitness/turnover/margin 分位数和 checks 分布。不得只按 family 最大 Sharpe 排名。

在上述统计前，必须按 `template_contract.md` 生成固定的三段表和逐模板 `实验成果评估 / 关键发现 / 改进方向`。代表 alpha 使用有符号最大 Sharpe/Fitness；基础 simulation screen 与 submission-only deferred 状态按格式契约区分，fallback 只能描述。没有 READY 的模板也必须出现在报告中。

### 3. IS-PnL 相关性

- 从 `simued_alpha_is_pnl` 读取每条 READY alpha 的 PnL 差分序列；兼容视图首项 `nan` 是预期行为。
- 按 F 预注册的缺失处理、最小重叠长度、correlation method 和 threshold 聚类。
- 相关性必须来自实际 PnL，不能从 expression 文本或 operator signature 推断。
- family shortlist 必须兼顾 density、质量和跨 cluster 覆盖；同一高相关 cluster 不得用多个代表虚增扩展或终检名额。

## 提交候选选择

- 只从 `analysis_eligibility=true` 的权威 run 选择本 run 的真实 `alpha_id`。
- 候选必须通过 B 预注册的 Sharpe、fitness、turnover、margin 与 simulation check 基础门槛。
- `LOW_SHARPE`、`LOW_FITNESS`、`LOW_TURNOVER`、`HIGH_TURNOVER`、`CONCENTRATED_WEIGHT`、`LOW_SUB_UNIVERSE_SHARPE`、`LOW_2Y_SHARPE` 等 simulation-resolved check 必须取得确定的通过结果；其 `PENDING/FAIL/ERROR` 或缺失均不能视为通过。
- `SELF_CORRELATION`、`DATA_DIVERSITY`、`PROD_CORRELATION`、`REGULAR_SUBMISSION` 的 `PENDING` 属于 submission-only 状态，记录为 deferred 并交给 L 重查，不得在 K 误判失败；已确定的 `FAIL/ERROR` 仍不得入选。
- 先按实际 IS-PnL cluster 去重，再综合稳定性、质量、density 和 pool 边际价值排序；禁止按单条最高 Sharpe 直接选取。
- 每个候选必须保存 experiment id、alpha id、family、cluster、完整 metrics/checks、PnL source 和选择理由。
- K 只证明候选值得进入慢速检查；self/prod correlation、完整 checks 和年度稳定性必须由 L 重新获取，K 不得预判 M 可提交。

## 输出

- `terminal_status.json`
- `run_export.json`
- `template_report.json`
- `template_report.md`
- `run_integrity.json`
- `isolated_experiments.json`
- `experiment_state_counts.json`
- `error_taxonomy.json`
- `family_density.json`
- `quality_distributions.json`
- `pnl_correlation_clusters.json`
- `family_shortlist.json`
- `best_alpha_candidates.json`
- `candidate_selection_audit.json`
- `next_action.json`：只能是 `L_SLOW_FINAL_CHECK`、`NEW_BATCH` 或 `STOP_OBJECTIVE_REACHED`；最后一种只允许在平台提交账本已证明累计目标完成时使用。
- `next_batch_run_spec.json`：仅在需要扩展或重新设计时存在，且新 run 必须从本流程 A 开始。
- `analysis_eligibility.json`
- `analysis_summary.md`
- `commands.md`
- `node_summary.md`

## 成功条件

- 每个 assigned candidate 在 state、错误、family 和 denominator 中恰好出现一次。
- 所有 family 比率都有原始计数和区间，不按小样本偶然值扩展。
- correlation cluster 可追溯到 alpha id、experiment id、family id 和 PnL source。
- 明确给出 run 是否具备终检候选选择与新 batch 扩展资格。
- 固定报告、预注册统计和最终 eligibility 分层保存，固定报告不能单独触发 L 或新 batch。
- `best_alpha_candidates.json` 为空时不得进入 L；累计目标未完成时必须选择 `NEW_BATCH`，弱结果不能结束 campaign。

## 下一跳

- `L 慢速终检`
- 创建新的独立 batch run，从本流程 A 开始
- 仅在预注册目标已完成时结束
