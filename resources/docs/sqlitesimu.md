# SQLite 批量回测插件

`wqb sqlitesimu` 把旧 `endless_simulate` 的三个常驻脚本收敛为一个可恢复的 CLI 工作流：

- `send_simulate_request.py`：表达式分组、批量 POST、保存 Location。
- `get_simulate_result.py`：按 Retry-After 轮询父任务和 child simulation。
- `get_is_pnl.py`：获取 alpha 详情与 PnL，生成 `simued_alpha_is_pnl`。

agent 或上游工作流只负责生成 manifest。插件负责认证、调度、重试、轮询、恢复和结果入库；运行期间不需要 agent 参与。

## 最短工作流

```cmd
wqb sqlitesimu run candidates.json --output run-result.json
```

默认数据库：

```text
local/sqlitesimu/simulations.sqlite3
```

拆分入库和执行时：

```cmd
wqb sqlitesimu enqueue candidates.json --output enqueue-result.json
wqb sqlitesimu resume <run_id> --output run-result.json
```

检查和导出：

```cmd
wqb sqlitesimu status <run_id>
wqb sqlitesimu export <run_id> --output alpha-results.json
```

显式废弃 run 时，先停止并确认 worker 已退出，再持久化取消状态：

```cmd
wqb sqlitesimu cancel <run_id> --reason obsolete_run --output cancel-result.json
```

`cancel` 保留所有历史和已有结果；除可能已发出 `POST /simulations` 的 `SIMULATE_UNKNOWN` 外，其余未完成待办转为 `CANCELLED` 并从运行队列删除。它不调用服务器撤销 simulation 的接口，也不能与活跃 worker 并发执行。有效 worker lease 会被默认拒绝；若进程已确认退出但租约尚未过期，显式增加 `--force-active-lease`。

## Manifest

完整格式：

```json
{
  "run": {
    "name": "generation-12",
    "enrichment_profile": "basic"
  },
  "metadata": {
    "workflow_id": "evolution-001"
  },
  "candidates": [
    {
      "expression": "rank(close)",
      "priority": 10,
      "metadata": {
        "generation": 12,
        "parent_id": "candidate-42",
        "hypothesis": "price rank baseline"
      },
      "settings": {
        "instrumentType": "EQUITY",
        "region": "USA",
        "universe": "TOP3000",
        "delay": 1,
        "decay": 5,
        "neutralization": "SUBINDUSTRY",
        "truncation": 0.08,
        "pasteurization": "ON",
        "unitHandling": "VERIFY",
        "nanHandling": "OFF",
        "language": "FASTEXPR",
        "visualization": false
      }
    }
  ]
}
```

也接受以下输入：

- 顶层直接是 simulation payload 数组。
- candidate 使用 `payload` 包裹原始 simulation body。
- REGULAR candidate 使用 `regular` 或 `expression`。
- SUPER candidate 使用 `combo` 和 `selection`。

候选由规范化 simulation payload 的 SHA-256 指纹去重。run、candidate 和 experiment 分离：同一表达式可以跨 run 复用 candidate，但每次 experiment 的 generation、parent、hypothesis 等 lineage 元数据彼此独立。

## 状态和恢复

主要状态：

```text
QUEUED -> BATCHED -> SIMULATING -> POLLING
       -> CHILD_POLLING -> SIM_DONE -> ENRICH_PNL -> READY
```

运行队列与历史账本分离：

- `simulation_queue` 是表达式待回测队列。只有拿到 alpha id，或已确认该表达式永久失败后，才在同一事务中删除。
- 拿到 alpha id 时，同一事务会先删除 `simulation_queue` 行，再写入 `enrichment_queue`。
- `enrichment_queue` 是 alpha 详情/PnL 待处理队列。只有详情和 PnL 都持久化、experiment 进入 `READY` 后才删除。
- `SIMULATE_UNKNOWN` 可能已经在服务器创建 simulation，因此不自动删除其 `simulation_queue` 行，必须先人工核对。
- queue 行会被真实 `DELETE`；`experiments`、batch、Location、API event 和结果表继续保留，因而删除待办不会破坏恢复、导出和审计。

`status` 和最终 run JSON 的 `queues.simulation`、`queues.enrichment` 可直接检查两级待办数量。旧数据库首次打开时会自动升级为 schema v3：v1 数据回填未完成队列，v2 的 simulation request 状态和事件统一迁移到 `SIMULATING / SIMULATE_UNKNOWN` 术语。

终止状态：

- `READY`：详情和 PnL 都已保存。
- `PERMANENT_FAILURE`：明确请求错误，或可重试读取错误超过预算。
- `SIMULATE_UNKNOWN`：`POST /simulations` 时连接中断或返回无法确认，可能已经在服务器创建 simulation。
- `CANCELLED`：用户显式终止的未完成 simulate 待办；历史仍可导出。

`SIMULATE_UNKNOWN` 会把 run 标为 `BLOCKED`。插件不会盲目再次 simulate，因为 `POST /simulations` 没有可用的幂等键，自动重跑可能制造重复 alpha。

每个 run 有 300 秒租约。同一数据库中第二个 worker 不能同时执行同一 run；进程硬退出后，需要等租约过期才能接管。若退出发生在 `SIMULATING`，接管时会转成 `SIMULATE_UNKNOWN`。

## 与旧脚本一致的行为

- REGULAR FASTEXPR 仍以 region 和 delay 为主要批次边界，普通区域单批最多 10 条。
- POST `/simulations` 成功必须是 `201`，并持久化 `Location`。
- `429` 和服务器并发限制不会消耗失败预算，按 `Retry-After` 继续等待。
- 客户端不设置 `8 / 4 / 3` 等并发槽位上限；持续发起 simulate 请求，由 BRAIN 的 `429` 和 `Retry-After` 提供背压。
- `204 / 401 / 429` 都按 `wqb.WQBSession` 的异常会话状态处理；即使两层重登耗尽，也只延期当前工作，不会把 experiment 写成永久失败。
- 父任务 `progress=0.35` 时，等待时间按批量大小除以 2 放大。
- 父任务完成后按 ordinal 将 children 映射回原 experiment，再逐个读取 child alpha id。
- 到期的父任务、child 和 enrichment 轮询优先于继续建批和 simulate，避免大批 manifest 让结果消费饥饿；未到 `not_before` 的任务不会阻塞新的 simulate 请求。
- enrichment 内部优先完成已经保存 detail 的 `ENRICH_PNL`，使每个 alpha 尽快闭环为 `READY` 并删除待办，而不是先积压整批 detail。
- 旧脚本识别的资源不足、执行异常、运行过久错误会重新排队。
- PnL 使用 record 第 2 列，先 forward-fill，再 diff；首项保存为 `nan`。
- alpha 详情扁平化为旧 24 字段，并从 `MATCHES_PYRAMID` 和 `DATA_USAGE:SINGLE_DATA_SET` 生成 pyramids。

## 有意保留的变动

| 位置 | 旧脚本 | sqlitesimu |
| --- | --- | --- |
| 源任务 | 结果落库后删除源表行，但完成前可能被再次随机抽中 | 两级 queue 真实消费删除；candidate/experiment 作为历史账本保留 |
| 尾批 | 少于 2 条会跳过 | 单条也 simulate，避免永久滞留 |
| 批次安全 | 只按 region、delay 分组，统一最多 10 条 | 额外隔离 instrument type、language；GLB 最多 5 条 |
| 并发 | 槽位检查已注释，依赖服务端 429 | 不做客户端槽位计数，依赖服务端 429/Retry-After |
| 重复 simulate | 异常后可能重新 POST | `POST /simulations` 结果不确定时阻塞，禁止盲目重跑 |
| 多进程 | 多线程加 SQLite lock | run 租约阻止两个 worker 重复消费 |
| 认证 | 脚本直接持有 EMAIL/PASSWORD | 使用 wqb-cli cookie/keyring/env；CoreClient 处理 `204 / 401 / 429`，耗尽后 sqlitesimu 再补 5 次重登 |
| 术语 | simulation POST 也常写作 submit | simulation 一律使用 simulate；submit 仅表示 `wqb alpha submit` 入库提交 |
| 详情/PnL | 两个线程并行，部分错误无限循环 | 分阶段持久化；普通读取错误受 `max-attempts` 限制 |
| 结果表 | 单个宽表 | 规范化表为主，保留同名兼容视图 |
| 输出 | 持续打印日志 | 执行过程静默，结束时输出一份 JSON |

这些变动用于确定性、崩溃恢复和工作流接入，不改变 alpha expression 或 BRAIN simulation payload。

## 自动续期边界

CoreClient 的默认策略参考安装环境中的 `wqb.WQBSession`：

- `204 / 401 / 429` 都触发重新认证，不只处理 `401`。
- 初始业务请求失败后最多重放 3 次；每次认证最多 POST 3 次，间隔 2 秒。
- 多线程同时发现失效时通过 generation 和锁共享一次成功登录。
- 登录前清除当前 session 中旧的 BRAIN cookie；旧版扁平 cookie 文件只加载到 API host 一次，避免父域和 host 域同时发送新旧会话值。
- 成功登录后立即保存 cookie；cookie 落盘失败会记录诊断，但不丢弃当前内存会话。
- `/authentication` 自身不递归触发自动认证，登录只有 `201` 视为成功。

`sqlitesimu` 在 CoreClient 耗尽后，再执行最多 5 轮显式登录和业务请求重放，轮间隔 2 秒。额外层的业务重放关闭 CoreClient 自动续期，保证这里严格是 5 轮，而不是递归放大。

若最终仍返回 `204 / 401 / 429`，runtime 会按 `Retry-After` 或默认间隔延期；父任务、child、详情和 PnL 轮询均不增加失败次数，run 保持可恢复。`POST /simulations` 的 `204` 也会重登并重放，这是为了与 `WQBSession` 一致；相较此前仅处理 `401` 且最多重放一次的 gateway，这是有意的行为变化。

alpha 等待与 simulation 轮询原先存在直接调用 `requests.Session` 和局部 Basic Auth 重试的路径；现在统一通过 CoreClient，避免绕过全局续期或重复放大认证请求。

## 结果模型

规范化结果位于：

- `runs`、`candidates`、`experiments`
- `simulation_queue`、`enrichment_queue`（只保存未消费待办）
- `simulation_batches`、`simulation_items`
- `alphas`、`alpha_metrics`、`alpha_checks`、`alpha_pnl`
- `api_events`、`outbox_events`

分析入口：

- `analysis_alpha_ready`：带 run/experiment/candidate lineage 的 READY 结果。
- `simued_alpha_is_pnl`：兼容旧分析代码的 24 列视图，`PnL` 仍为逗号分隔差分序列。

`wqb sqlitesimu export` 还会输出所有 experiment 的 payload、lineage、attempts、state、alpha id 和 last error，以及 READY alpha 的完整 checks，供后续批量诊断和固定格式报告。

建议新分析读取 `analysis_alpha_ready` 和规范化 PnL 表；旧 notebook 可以继续读取 `simued_alpha_is_pnl`。

## BatchSimu 模板格式与报告

模板 manifest 可在入库前独立校验，不会初始化或修改 SQLite：

```cmd
wqb sqlitesimu template-validate simulation_manifest.json --output template_validation.json
```

严格格式要求包括两行模板 header、唯一 `_variable` 中间变量、最后的 `template_LLM` 赋值与返回行、无未解析 placeholder，以及 family/version/epoch、字段角色、抽样、完整表达式、计算正文和 settings 的 hash lineage。

权威 run 到达终态并 export 后，可生成 notebook 兼容的固定三段统计和逐模板评估：

```cmd
wqb sqlitesimu template-report run_export.json --output template_report.json --markdown-output template_report.md
```

三段分别是 `template alphas performance each template`、`template alphas checks statistics` 和 `template alphas best performance each metric`。代表选择使用有符号最大 Sharpe/Fitness，并限制在各 template 内；报告不会把 `CANCELLED/BLOCKED/SIMULATE_UNKNOWN` run 判作可扩展。

## 退出码

- `0`：全部完成。
- `2`：达到 `--max-runtime-seconds`，run 仍可 resume。
- `3`：完成，但存在永久失败。
- `4`：存在 `SIMULATE_UNKNOWN`，需要人工核对服务器状态。
- `1`：参数、认证、数据库或未分类运行错误。

## SQLite 约束

数据库应放在运行 worker 的本地磁盘。不要把活跃 WAL 数据库放在 SMB/NFS/网盘同步目录；如需跨机器调度，应把 store 接口替换成服务型数据库，而不是共享 SQLite 文件。
