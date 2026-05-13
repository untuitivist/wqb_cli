# K_结果诊断

## 目标
- 读取 `J_并行回测` 产出的真实 `alpha_id` 列表。
- 通过 `wqb_core.alpha.get_alpha_details.py` 拉取每个 alpha 的详情。
- 聚合首轮诊断结论，判断：
  - 哪些候选相对更值得保留；
  - 哪些主要失败在基础质量；
  - 哪些主要失败在 overused data / diversity；
  - 是否应回退到 `E` 或 `I`。

## 输入
- `J` 的 `alpha_candidates__{REGION}_D{DELAY}_{CATEGORY}.json`
- 当前主塔三元组：`region / delay / category`

## 输出
- `alpha_details__{REGION}_D{DELAY}_{CATEGORY}.json`
- `diagnosis__{REGION}_D{DELAY}_{CATEGORY}.json`
- `survivors__{REGION}_D{DELAY}_{CATEGORY}.json`
- `node_summary.md`

## 规则
- 只用命令行调用 `wqb_core`。
- 首轮诊断优先使用 `get_alpha_details`，不默认拉完整 `PnL`。
- 如果上游 `J` 的回测打开了 `visualization`，后续应优先保留这些结果，方便补充图形化诊断。
- 诊断时重点看：
  - `sharpe`
  - `fitness`
  - `turnover`
  - `margin`
  - `drawdown`
  - `LOW_SUB_UNIVERSE_SHARPE`
  - `MATCHES_PYRAMID`
  - `ALPHA_DATA_CATEGORY_DIVERSITY / Overused data`
- 先区分“结构可跑但质量弱”和“质量尚可但数据拥挤/重复”。
- 输出必须给出：
  - 推荐保留批次
  - 推荐回退节点
  - 回退原因
