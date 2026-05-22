# E Super own/notown 判断

## 目标

判断是否可做 super own/notown，并为 H 提供 super 约束。

## 输入

必要：

- C 的 `regular_or_super_decision.md`。

可选：

- 最近 purple、tag 为 `!OWN` 的 super alpha 作为额度检查参考。

## 只允许的 CLI

```powershell
wqb alpha list --output <node_dir>/super_alpha_candidates.json
wqb alpha get <alpha_id> --output <node_dir>/reference_super_alpha.json
wqb alpha check <alpha_id> --max-wait-seconds 900 --output <node_dir>/reference_super_check.json
wqb sim super-selection --output <node_dir>/super_selection_options.json
```

## 输出

必要：

- `super_feasibility.md`：own/notown 是否可做、额度和风险。
- `super_constraints.json`：sharpe >= 5、fitness >= 5、prodcorr <= 0.5、check 通过。
- `node_summary.md`

可选：

- `reference_super_alpha.json`
- `reference_super_check.json`

## 成功条件

- 明确本轮是否走 super 分支。
- 如果走 super，给 H/I/J 明确约束。

## 下一跳

- `H 经济学机制假设`
