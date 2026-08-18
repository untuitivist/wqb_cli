# L 扩展或终止

## 目标

根据 K 的预注册统计和真实 PnL cluster，在 `EXPAND` 与 `STOP` 之间作出最终决定。L 只制定下一 batch run 的研究规格或终止当前研究，不生成 candidate、不启动 worker、不提交 Alpha。

## 输入

- B 的 objective、budget 和 stop conditions
- F 的 analysis contract
- K 的 integrity、eligibility、density、quality、correlation 和 shortlist artifacts

## 决策条件

只有同时满足以下条件才能 `EXPAND`：

- `analysis_eligibility = true`
- family READY coverage 达到 F 的最小样本要求
- usable density 与置信区间优于预注册基线，而非仅有单条极值
- 错误率未显示结构、unit 或 operator 契约失效
- 被选 family 覆盖不同 PnL clusters，且仍有未采样的有效 population
- 剩余 simulation budget 和最大轮数允许扩展

任一条件不满足则 `STOP`。停止可以记录“证据不足、需要未来重新设计”，但不能把当前 alpha 交给提交动作。

## 扩展分配

- 只扩展少数具有稳定密度且跨 cluster 的 family。
- 社区案例中每个领先 family 约扩到 1600 条是参考量级，不是固定配额。
- 实际配额由未采样 population、置信区间宽度、cluster diversity 和剩余预算推导。
- 不重新抽取首轮已测试 identity，不增加 sign twin 或 wrapper-only 变体。
- 扩展必须创建新的独立 batch run，并从该流程的 A 节点开始；当前 J 数据库保持只读历史记录。

## 输出

- `decision.json`：`decision` 只能是 `EXPAND` 或 `STOP`，并列出证据和否决条件。
- `selected_families.json`
- `cluster_allocation.json`
- `next_batch_run_spec.json`：仅在 EXPAND 时存在，包含 parent run、family version、未采样空间、预算和固定设置要求。
- `termination_report.md`：仅在 STOP 时存在。
- `commands.md`
- `node_summary.md`

## 禁止事项

- 不按最高 Sharpe 单点选择 family。
- 不在相关性聚类完成前扩展。
- 不把不同 PnL cluster 中的代表线性混成一个 expression。
- 不直接 patch、tag 或 submit 任一 alpha。
- 不产生指向其他研究流程的 handoff。

## 成功条件

- 决策完全可由 K 和预注册合同复算。
- EXPAND 时下一 run 的范围明确且不复用可写数据库；STOP 时本流程终止且无提交副作用。

## 下一跳

- `EXPAND`：创建新的独立 batch run，从 A 开始。
- `STOP`：本轮结束。
