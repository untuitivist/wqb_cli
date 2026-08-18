# J SQLite 入库、启动与交接

## 目标

把 I 的已验证 manifest 原样入库到本 run 独立 SQLite，启动 `wqb sqlitesimu resume` worker，验证 worker 已接管后写出监控交接。J 不参与逐条 backtest。

## 输入

- A 的 `storage_plan.json`
- C 的 `settings_identity.json`
- I 的 `simulation_manifest.json`
- I 的 `validation_report.json`
- I 的 `template_validation.json`
- I 的 `candidate_identity_index.json`

## 推荐命令

```cmd
wqb sqlitesimu template-validate <i_node_dir>\simulation_manifest.json --output <node_dir>\template_validation_before_enqueue.json
wqb sqlitesimu init --db <node_dir>\simulations.sqlite3 --output <node_dir>\init_result.json
wqb sqlitesimu enqueue <i_node_dir>\simulation_manifest.json --db <node_dir>\simulations.sqlite3 --output <node_dir>\enqueue_result.json
wqb sqlitesimu status <run_id> --db <node_dir>\simulations.sqlite3 --output <node_dir>\status_before_launch.json
start "" /b cmd.exe /d /s /c "wqb sqlitesimu resume <run_id> --db <node_dir>\simulations.sqlite3 --output <node_dir>\worker_result.json 1><node_dir>\worker.stdout.log 2><node_dir>\worker.stderr.log"
wqb sqlitesimu status <run_id> --db <node_dir>\simulations.sqlite3 --output <node_dir>\status_after_launch.json
```

宿主 workflow runner 也可以用自己的后台进程管理器启动同一条 `resume` 命令。不得为了后台运行而生成会修改候选或数据库的辅助脚本。

## 输出

- `simulations.sqlite3` 及其 SQLite sidecar 文件
- `init_result.json`
- `enqueue_result.json`
- `status_before_launch.json`
- `status_after_launch.json`
- `template_validation_before_enqueue.json`
- `worker_launch.json`：启动命令、时间、进程引用和日志路径。
- `worker_handoff.json`：db、run_id、manifest hash、settings hash、candidate/family counts、status/restart/export 命令和终态集合。
- `commands.md`
- `node_summary.md`

## 入库闸门

- I validation verdict 或 J 的重复 `template-validate` 不是 true 时禁止 enqueue。
- `enqueue_result.accepted` 必须等于 I candidate count，`duplicates` 必须符合 I 的预期；任何差异都先停止，不得在 J 补 candidate。
- enqueue 后记录真实 `run_id`，后续命令不能用 manifest name 代替。
- J 不执行 SQL UPDATE/DELETE，不直接修改 state、attempts 或 alpha id。

## Agent 边界

worker 启动并在 `status_after_launch.json` 中显示非终态进展或已完成后，J 立即交接：

- CoreClient 对 `204 / 401 / 429` 做全局续期与重放，sqlitesimu 耗尽后再补 5 次显式重登。
- worker 不做客户端并发槽位计数，持续发起 simulate 请求并由服务器 `429 / Retry-After` 控制背压。
- worker 自己轮询、恢复、抓取 alpha detail/PnL 和写库；simulation/enrichment 阶段完成后原子消费对应 queue 行。
- agent 不读取单条 alpha，不修改 manifest，不根据中间结果新增表达式。
- 监控只运行 `wqb sqlitesimu status` 并报告 state、experiment counts 和两级 `queues` 计数；禁止持续打印 worker log。
- worker 异常退出时只用相同 db/run_id 重启 `resume`；`SIMULATE_UNKNOWN` 不得盲目再次 simulate。

## 显式终止

用户废弃本 run 时，先停止并确认 worker 进程已经退出，再执行：

```cmd
wqb sqlitesimu cancel <run_id> --reason <reason> --db <node_dir>\simulations.sqlite3 --output <node_dir>\cancel_result.json
wqb sqlitesimu status <run_id> --db <node_dir>\simulations.sqlite3 --output <node_dir>\status_after_cancel.json
```

`cancel` 不向服务器发送撤销 simulation 请求。已处于 `SIMULATING` 的工作转成 `SIMULATE_UNKNOWN` 并保留 simulation queue，其他未完成工作转成 `CANCELLED` 并消费两级待办；READY、alpha、PnL、batch、Location、事件和 candidate/experiment 历史全部保留。禁止只杀 worker 而让 run 永久停在 `RUNNING`，也禁止在 worker 仍活着时并发执行 cancel。若进程已确认退出但有效 lease 仍残留，可在 cancel 命令中增加 `--force-active-lease`；该参数不能代替进程检查。

## 成功条件

- 本 run 数据库、真实 run_id、worker 和恢复命令均可定位。
- manifest 与 enqueue 计数一致，worker 已接管。
- `alpha_submission_allowed` 仍为 false。

## 下一跳

- run 达到终态后进入 K；`CANCELLED/BLOCKED` 只允许描述性报告并在 L 停止，非终态只继续 worker 监控。
