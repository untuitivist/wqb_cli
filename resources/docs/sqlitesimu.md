# SQLite 批量回测插件

`wqb sqlitesimu` 把旧 `endless_simulate` 的三个常驻脚本收敛为一个可恢复的 CLI 工作流：

- `send_simulate_request.py`：表达式分组、批量 POST、保存 Location。
- `get_simulate_result.py`：按 Retry-After 轮询父任务和 child simulation。
- `get_is_pnl.py`：获取 alpha 详情与 PnL，生成 `simued_alpha_is_pnl`。

agent 或上游工作流只负责生成 manifest。插件负责认证、调度、重试、轮询、恢复和结果入库；运行期间不需要 agent 参与。

## 最短工作流

```powershell
wqb sqlitesimu run candidates.json --output run-result.json
```

默认数据库：

```text
local/sqlitesimu/simulations.sqlite3
```

拆分入库和执行时：

```powershell
wqb sqlitesimu enqueue candidates.json --output enqueue-result.json
wqb sqlitesimu resume <run_id> --output run-result.json
```

检查和导出：

```powershell
wqb sqlitesimu status <run_id>
wqb sqlitesimu export <run_id> --output alpha-results.json
```

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
QUEUED -> BATCHED -> SUBMITTING -> POLLING
       -> CHILD_POLLING -> SIM_DONE -> ENRICH_PNL -> READY
```

运行队列与历史账本分离：

- `simulation_queue` 是表达式待回测队列。只有拿到 alpha id，或已确认该表达式永久失败后，才在同一事务中删除。
- 拿到 alpha id 时，同一事务会先删除 `simulation_queue` 行，再写入 `enrichment_queue`。
- `enrichment_queue` 是 alpha 详情/PnL 待处理队列。只有详情和 PnL 都持久化、experiment 进入 `READY` 后才删除。
- `SUBMIT_UNKNOWN` 可能已经在服务器创建任务，因此不自动删除其 `simulation_queue` 行，必须先人工核对。
- queue 行会被真实 `DELETE`；`experiments`、batch、Location、API event 和结果表继续保留，因而删除待办不会破坏恢复、导出和审计。

`status` 和最终 run JSON 的 `queues.simulation`、`queues.enrichment` 可直接检查两级待办数量。schema v1 数据库首次由新版本打开时会自动升级为 v2，并根据 experiment 状态回填尚未完成的队列项。

终止状态：

- `READY`：详情和 PnL 都已保存。
- `PERMANENT_FAILURE`：明确请求错误，或可重试读取错误超过预算。
- `SUBMIT_UNKNOWN`：POST 时连接中断或返回无法确认，可能已经在服务器创建任务。

`SUBMIT_UNKNOWN` 会把 run 标为 `BLOCKED`。插件不会盲目重发，因为 POST simulation 没有可用的幂等键，自动重发可能制造重复 alpha。

每个 run 有 300 秒租约。同一数据库中第二个 worker 不能同时执行同一 run；进程硬退出后，需要等租约过期才能接管。若退出发生在 `SUBMITTING`，接管时会转成 `SUBMIT_UNKNOWN`。

## 与旧脚本一致的行为

- REGULAR FASTEXPR 仍以 region 和 delay 为主要批次边界，普通区域单批最多 10 条。
- POST `/simulations` 成功必须是 `201`，并持久化 `Location`。
- `429` 和服务器并发限制不会消耗失败预算，按 `Retry-After` 继续等待。
- 客户端不设置 `8 / 4 / 3` 等并发槽位上限；持续提交，由 BRAIN 的 `429` 和 `Retry-After` 提供背压。
- `204 / 401 / 429` 都按 `wqb.WQBSession` 的异常会话状态处理；即使两层重登耗尽，也只延期当前工作，不会把 experiment 写成永久失败。
- 父任务 `progress=0.35` 时，等待时间按批量大小除以 2 放大。
- 父任务完成后按 ordinal 将 children 映射回原 experiment，再逐个读取 child alpha id。
- 旧脚本识别的资源不足、执行异常、运行过久错误会重新排队。
- PnL 使用 record 第 2 列，先 forward-fill，再 diff；首项保存为 `nan`。
- alpha 详情扁平化为旧 24 字段，并从 `MATCHES_PYRAMID` 和 `DATA_USAGE:SINGLE_DATA_SET` 生成 pyramids。

## 有意保留的变动

| 位置 | 旧脚本 | sqlitesimu |
| --- | --- | --- |
| 源任务 | 结果落库后删除源表行，但完成前可能被再次随机抽中 | 两级 queue 真实消费删除；candidate/experiment 作为历史账本保留 |
| 尾批 | 少于 2 条会跳过 | 单条也提交，避免永久滞留 |
| 批次安全 | 只按 region、delay 分组，统一最多 10 条 | 额外隔离 instrument type、language；GLB 最多 5 条 |
| 并发 | 槽位检查已注释，依赖服务端 429 | 不做客户端槽位计数，依赖服务端 429/Retry-After |
| 重复提交 | 异常后可能重新 POST | POST 结果不确定时阻塞，禁止盲重发 |
| 多进程 | 多线程加 SQLite lock | run 租约阻止两个 worker 重复消费 |
| 认证 | 脚本直接持有 EMAIL/PASSWORD | 使用 wqb-cli cookie/keyring/env；CoreClient 处理 `204 / 401 / 429`，耗尽后 sqlitesimu 再补 5 次重登 |
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

alpha 等待与 submit 轮询原先存在直接调用 `requests.Session` 和局部 Basic Auth 重试的路径；现在统一通过 CoreClient，避免绕过全局续期或重复放大认证请求。

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

`wqb sqlitesimu export` 还会输出所有 experiment 的 payload、lineage、attempts、state、alpha id 和 last error，供后续批量诊断失败表达式。

建议新分析读取 `analysis_alpha_ready` 和规范化 PnL 表；旧 notebook 可以继续读取 `simued_alpha_is_pnl`。

## 退出码

- `0`：全部完成。
- `2`：达到 `--max-runtime-seconds`，run 仍可 resume。
- `3`：完成，但存在永久失败。
- `4`：存在 `SUBMIT_UNKNOWN`，需要人工核对服务器状态。
- `1`：参数、认证、数据库或未分类运行错误。

## SQLite 约束

数据库应放在运行 worker 的本地磁盘。不要把活跃 WAL 数据库放在 SMB/NFS/网盘同步目录；如需跨机器调度，应把 store 接口替换成服务型数据库，而不是共享 SQLite 文件。
