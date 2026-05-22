# B 平台机会与等级差距

## 目标

读取 consultant performance、消息、活动和等级硬指标，判断当前季度已达成等级与下一等级 gap。

## 输入

必要：

- A 的 `auth_status.json`。

可选：

- 上一季度 `currentLevel`。

## 推荐使用的 CLI

```powershell
wqb user consultant-summary --output <node_dir>/consultant_summary.json
wqb consultant summary --output <node_dir>/consultant_summary_compat.json
wqb user messages-summary --output <node_dir>/messages_summary.json
wqb user messages --output <node_dir>/messages.json
wqb user messages --limit 50 --offset 0 --order=-dateCreated --type ANNOUNCEMENT --output <node_dir>/recent_announcements_page1.json
wqb user messages --limit 50 --offset 50 --order=-dateCreated --type ANNOUNCEMENT --output <node_dir>/recent_announcements_page2.json
wqb event list --output <node_dir>/events.json
```

## 输出

必要：

- `consultant_summary.json`
- `level_gap.md`
- `current_theme.md`
- `platform_opportunities.md`
- `node_summary.md`

可选：

- `messages_summary.json`
- `messages.json`
- `recent_announcements_page1.json`
- `recent_announcements_page2.json`
- `recent_theme.md`：从 `recent_announcements_page1.json` 和 `recent_announcements_page2.json` 中按 `dateCreated` 由近到远查找标题或正文包含 `Theme` / `theme` 的公告，记录最近 theme 的名称、时间、multiplier、duration、region/turnover 等约束。
- `events.json`

## Current theme summary

`current_theme.md` must summarize themes that are active at the current run date.
Use `dateCreated` only as announcement time; active status must be judged from the theme `Duration` in the announcement body.
If multiple themes are active at the current run date, list all of them and mark the main constraints for each theme.
At minimum record:
- `run_date`
- `active_theme_count`
- theme name
- duration
- multiplier
- alpha type, such as regular alpha or regular power pool alpha
- region / delay / universe / neutralization requirements
- turnover / HTVR / after-cost / dataset restrictions
- source announcement id, title, and `dateCreated`

When the current date is 2026-05-22, the active announcements from the latest page include:
- `After Cost HTVR Theme`: May 11-May 24, 3X regular alphas, USA, HTVR base conditions, turnover > 20%, high-turnover returns ratio > 0.75 or PnL realization < 20, after-cost Sharpe > 1.0.
- `MEA Region Theme`: May 4-May 31, 1.5X regular alphas, alpha must be simulated in MEA.
- `All regions/D0 Power Pool May\`26`: May 1-May 31, 1X regular power pool alphas, power pool alpha must use delay 0.

## 等级硬指标

- GOLD：无额外硬指标记录。
- EXPERT：Signals >= 20；Pyramids Completed >= 10；任一 combined performance >= 0.5。
- MASTER：Signals >= 120；Pyramids Completed >= 30；任一 combined performance >= 1。
- GRAND MASTER：Signals >= 220；Pyramids Completed >= 60；任一 combined performance >= 2。

combined performance 包括：

- Combined Alpha Performance
- Combined Selected Alpha Performance
- Combined Power Pool Alpha Performance
- Combined Osmosis Performance

## 成功条件

- 明确当前季度等级目标、已达成项、下一等级 gap。
- 给出本轮研究应优先服务的 performance 或点塔方向。

## 下一跳

- `D Regular 主塔选择`
- `H 经济学机制假设`
