# C 研究方向与提交额度

## 目标

用平台记录判断今日 regular/super 提交额度、已提交方向，以及 super own/notown 是否值得进入。

## 输入

必要：

- A 的认证态。

可选：

- B 的等级差距。

## 只允许的 CLI

```powershell
wqb alpha list --limit 100 --order=-dateSubmitted --date-submitted-after <et_today_00:00:00-04:00_or_-05:00> --date-submitted-before <et_tomorrow_00:00:00-04:00_or_-05:00> --output <node_dir>/alphas_today_source.json
wqb alpha list --limit 100 --type REGULAR --order=-dateSubmitted --date-submitted-after <et_today_00:00:00-04:00_or_-05:00> --date-submitted-before <et_tomorrow_00:00:00-04:00_or_-05:00> --output <node_dir>/regular_alphas_today.json
wqb alpha list --limit 100 --type SUPER --order=-dateSubmitted --date-submitted-after <et_today_00:00:00-04:00_or_-05:00> --date-submitted-before <et_tomorrow_00:00:00-04:00_or_-05:00> --output <node_dir>/super_alphas_today.json
wqb user alphas-summary --output <node_dir>/alphas_summary.json
wqb user pyramid-alphas --output <node_dir>/pyramid_alphas.json
wqb user pyramid-multipliers --output <node_dir>/pyramid_multipliers.json
```

## 输出

必要：

- `submission_quota.md`：按美东提交日，用 `filter_alpha` 等价结果判断今日提交数。
- `used_research_directions.md`：今日已用 region/delay/category/type。
- `regular_or_super_decision.md`
- `node_summary.md`

可选：

- `alphas_today_source.json`
- `regular_alphas_today.json`
- `super_alphas_today.json`
- `alphas_summary.json`
- `pyramid_alphas.json`
- `pyramid_multipliers.json`

## 成功条件

- 明确 regular 今日剩余额度。
- 明确 super 今日剩余额度。
- 明确 super notown 是否可继续检查。

## 下一跳

- `D Regular 主塔选择`
- `E Super own/notown 判断`
