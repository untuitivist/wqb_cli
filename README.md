# WQB CLI

这个仓库包含两部分：

- `wqb_core/`：WorldQuant BRAIN 常用接口的 Python 源脚本和会话封装。
- `workgraph/`：面向 agent 的 WQB alpha 研究工作图。

旧的 `workflow/` 目录仍然保留，但它不是当前 workgraph 的 runner。
不要把 `workflow/nodes/*/run.bat` 接入新的 `workgraph/regular`。

## 当前主线

当前实现的是 REGULAR alpha 工作图：

```text
workgraph/regular/
```

它的目标不是一次性生成一个 alpha，而是让 workagent 和 nodesubagent 在可审计、可恢复、可监督的约束下完成研究流程：

- 点塔是第一优先级。
- 其次服务长期目标：高 Value Factor / VF、高 weight、Grand Master readiness。
- 每个节点一次运行一个文件夹。
- 节点过程、证据、校验、结果都要落盘，供后续节点读取。
- 后续节点不能依赖聊天历史，只能依赖上游 artifact。

## 目录结构

```text
wqb_core/             BRAIN API 源脚本和 mixin
workgraph/regular/    当前可用的 REGULAR 工作图
workgraph/super/      未来 SUPER 工作图占位，当前不要使用
workflow/             旧工作流，保留但不接入新 runner
docs/data_all/        本地 dataset/datafield 元数据
research_runs/        新 workgraph 的运行输出目录
```

## 运行目录约束

每次 workgraph 运行只能写入一个目录：

```text
research_runs/run_YYYYMMDD_HHMMSS/
```

运行中的 workagent 和 nodesubagent 不应在其他位置创建或修改业务输出。
开发 workgraph 源文件本身时除外。

每个节点运行目录形如：

```text
research_runs/run_YYYYMMDD_HHMMSS/nodes/01_A_login_shared_auth/
```

节点必须产出公共 bundle：

```text
node_input.json
node_result.json
process_log.md
handoff.md
evidence_index.json
validation_report.json
outputs/
```

## Agent 分工

### workagent

workagent 只负责调度和监督：

- 初始化 run 目录。
- 创建节点任务。
- 分配 nodesubagent。
- 校验节点输出。
- 更新 `graph_state.json`。
- 决定下一节点或停止。

workagent 不执行节点业务，不补写节点输出。

### nodesubagent

nodesubagent 一次只执行一个节点：

- 只读 `node_input.json`、节点 contract、显式上游 artifact 和必要的只读源文件。
- 只写自己的节点目录。
- 必须记录过程、证据、输出和校验结果。
- 不能修改 `graph_state.json`。
- 不能运行后续节点。

## 核心工具

新 workgraph 应优先使用 `wqb_core` 里的源脚本，而不是临时创建 wrapper。

常用入口：

```powershell
python workgraph\regular\scripts\init_run.py
python workgraph\regular\scripts\create_node_task.py ...
python workgraph\regular\scripts\validate_node_bundle.py ...
python workgraph\regular\scripts\validate_run_scope.py ...
python workgraph\regular\scripts\update_graph_state.py ...
python workgraph\regular\scripts\audit_run.py ...
```

节点业务脚本优先使用源脚本，例如：

```powershell
python wqb_core\user\get_authentication.py --output outputs\auth_status.json
python wqb_core\user\get_pyramid_alphas.py --scope quarter --output outputs\current_quarter_pyramids.json
python wqb_core\simulation\simulate.py --target @file:alpha.json --mode preview --output outputs\simulation_results.json
python wqb_core\simulation\concurrent_simulate.py --targets @file:batch.json --mode preview --output outputs\simulation_results.json
```

## Python Alpha 约束

当前 Python Alpha 支持范围较窄：

- 只支持 REGULAR alpha。
- 只走单 alpha 回测：`wqb_core/simulation/simulate.py`。
- 不走 `concurrent_simulate.py` 批量路径。
- 只能使用 `type = "MATRIX"` 的 datafield。
- `@alpha(data=[...])` 中声明的字段必须来自 E 节点的 `available_datafields.json`。

校验入口：

```powershell
python workgraph\regular\scripts\validate_python_alpha.py candidate.json --fields available_datafields.json --require-matrix-fields
```

是否启用 Python Alpha 必须在 E 节点之前确定：

- D 或 BCD' 输出 `implementation_mode`。
- E 根据 `implementation_mode` 筛字段类型。
- I 只能按该模式生成 FASTEXPR 或 PYTHON candidate。

## 安装

建议使用本地 Conda 环境 `WQBRAIN`：

```powershell
conda create -n WQBRAIN python=3.12 -y
conda activate WQBRAIN
python -m pip install -e .
```

创建本地凭据文件：

```powershell
Copy-Item .env.example .env
```

然后编辑 `.env`，设置 `EMAIL` / `PASSWORD` 或 `WQB_EMAIL` / `WQB_PASSWORD`。

`wqb_core` 可复用 `.wqb_cli_auth/cookies.json` 中的登录状态。
`.env` 和 `.wqb_cli_auth/` 都是本地状态，不应提交。

## 不应提交

不要提交：

- `.env`
- `.wqb_cli_auth/`
- `research_runs/`
- `docs/research_runs/`
- `__pycache__/`
- 浏览器临时 profile，例如 `wqb_core/.tmp_edge_profile/`

