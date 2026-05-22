# D Regular 主塔选择

## 目标

选择本轮 regular 主塔。
D 必须服务当前季度 genius 定级，不允许把全部历史塔当作当前季度塔。
点塔为最高优先级，其次才是提升 performance。

## 输入

必要：

- B 的 `consultant_summary.json`。
- B 的 `level_gap.md`。
- C 的 `submission_quota.md` 与 `used_research_directions.md`。

可选：

- 历史 K 诊断。
- 全部历史塔背景，但只能作为背景，不能作为当前季度塔。

## 推荐使用的 CLI

```powershell
wqb user consultant-summary --output <node_dir>/consultant_summary.json
wqb user pyramid-alphas --start-date <quarter_start> --end-date <quarter_end> --output <node_dir>/quarter_pyramid_alphas.json
wqb user pyramid-multipliers --start-date <quarter_start> --end-date <quarter_end> --output <node_dir>/quarter_pyramid_multipliers.json
wqb user user-diversity <user_id> --output <node_dir>/diversity.json
wqb data categories --output <node_dir>/data_categories.json
```

禁止无参数调用 `wqb user pyramid-alphas` 并把结果当作当前季度塔。
无参数结果是全部塔 counts。
D 必须使用 `consultant_summary.json` 中的当前季度起止日期，或按当前日期计算季度起止日期，再传入 `--start-date` / `--end-date`。

## 输出

必要：

- `genius_quarter_context.json`：当前季度、当前 geniusLevel、当前季度 Signals、Pyramids Completed、下一等级 gap。
- `quarter_tower_status.json`：当前季度各 region/delay/category 塔状态，必须来自带 `startDate/endDate` 的 `pyramid-alphas`。
- `main_tower.json`：region、delay、universe、category、目标塔、优先级原因。
- `tower_rationale.md`：为什么这个塔优先。
- `node_summary.md`

如果当前 CLI 无法直接拿到季度塔，必须输出：

- `cli_gap.md`：说明缺少季度塔 endpoint 或参数。
- `quarter_tower_status_from_recent_alphas.json`：用当前季度 `dateSubmitted` / 有效 alpha 近似构造，并明确标注 approximate。

可选：

- `all_time_pyramid_alphas_background.json`：全量历史塔背景，不能用于季度塔结论。
- `avoid_towers.md`：不做的塔及原因。

## 决策规则

- `currentLevel` 是上一季度确定等级；D 服务的是下一季度定级。
- `performance.current.geniusLevel` 和 `performance.currentQuarter` 是 D 的时间口径。
- `pyramidCount` 缺口优先映射到当前季度未点亮或接近点亮的塔。
- 季度塔必须用 `pyramid-alphas?startDate=<quarter_start>&endDate=<quarter_end>` 获取。
- 无参数 `pyramid-alphas` 是全部塔，不能作为当前季度塔判断依据。
- D1 点完才能做 D0。
- 远离 D0，除非 D1 目标已满足或本轮明确需要。
- 点塔收益高于 overused data 忧虑。
- 如果 C 显示 regular 今日额度为 0，仍继续到 H/I/J 形成候选，但 M 不执行 regular 提交。

## 成功条件

- 主塔选择足够具体，能直接约束 F、G、H、I、J。
- 若使用近似季度塔，必须清楚标注近似来源和不确定性。

## 下一跳

- `F 数据与字段可行性`
- `G 社区与文档经验`
- `H 经济学机制假设`

## 规则修正：当前季度点塔定义

- 点亮塔的硬定义：当前季度某个 `region / delay / category` 的 `alphaCount >= 3`。
- `alphaCount = 0`、`alphaCount = 1`、`alphaCount = 2` 都视为未点亮或未补足，不能当作已点亮。
- D 必须用 `wqb user pyramid-alphas --start-date <quarter_start> --end-date <quarter_end>` 获取当前季度塔状态。
- 禁止用无参 `wqb user pyramid-alphas` 的全量历史 counts 判断当前季度塔是否点亮。
- D 选择主塔时必须优先考虑当前季度 `alphaCount < 3` 的 D1 塔；D0 仍然在 D1 补足前降级。
- `main_tower.json` 必须写入 `alphaCount`、`neededToLight = max(0, 3 - alphaCount)`、`multiplier` 和选择理由。
## 硬规则：主塔与主信号一致

- D 选择的目标塔决定本轮主信号 category。
- 目标塔为 MODEL，则主信号必须来自 MODEL 字段或模型机制；目标塔为 PV，则主信号必须来自 price/volume 机制。
- 禁止选择某个塔后，在 H/I/J 中用其他塔的强信号作为主要收益来源，再用少量目标塔字段蹭分类。
- 如果该塔纯机制不可行，D/K 应切换主塔，而不是允许混信号。
