# wqb-cli

[English](README.md) | 简体中文

`wqb-cli` 是一个 agent-native 的 WorldQuant BRAIN 命令行工具，用于把认证、API 查询、alpha 检查、回测提交、正式提交、本地数据筛选和社区数据检索组织成可复用的研究流程。

它优先服务编码 agent 和长流程研究 agent，而不是只给人手工敲命令使用的薄封装。命令会输出结构化 JSON，保留原始 API 上下文，等待平台异步结果，并自然适配可重复的研究节点流程。

- 仓库：[untuitivist/wqb_cli](https://github.com/untuitivist/wqb_cli)
- 作者：[wiz](https://github.com/untuitivist)
- 许可证：GPL-3.0-only with Commons Clause，详见 [LICENSE](LICENSE)。

## Agent-Native 设计

`wqb-cli` 的设计目标是让 agent 可以在不依赖浏览器状态、不依赖人工点击的情况下，可检查、可复用、可追踪地操作 BRAIN 工作流：

- 命令输出结构化结果，可用 `--output` 保存，并交给后续 workflow 节点继续使用。
- simulation、submit check、alpha check、recordsets 等异步结果都有明确等待语义。
- 随包提供 API inventory 和命令文档，agent 可以本地检查 endpoint 与参数。
- `workflow/` 下提供可复用节点文档，明确输入、允许命令、必要输出和成功条件。
- 本地数据命令读取 `local/` 下的稳定文件，不直接抓取浏览器或插件缓存。
- 命令输出保留 request/response 上下文，包括状态码、参数、Location、retry 事件和返回体。
- 不保留 dry-run 分支，避免自动化流程歧义：命令要么真实调用 API 并等待结果，要么明确失败。

## 功能概览

- 调用 `https://api.worldquantbrain.com` 的 API 命令。
- 登录与 cookie 本地保存。
- REGULAR FASTEXPR、REGULAR PYTHON、SUPER 回测命令。
- alpha 列表、详情、检查、recordsets、相关性、提交等命令。
- 基于 `data_all` / `all_data.pickle` 的本地字段筛选。
- WebDataScope 社区数据导入与本地检索。
- 随包发布的 API endpoint inventory 与命令文档。
- `workflow/` 下的结构化研究节点文档。

## 重要说明

- 本项目不隶属于 WorldQuant 或 WorldQuant BRAIN。
- 会修改平台状态的命令会直接发送真实 API 请求；当前没有 dry-run 模式。
- 需要等待平台异步结果的命令会等待最终结果、失败或超时后再返回；simulation 类等待默认超时通常为 900 秒。
- 本地数据不提交到 Git。凭证、cookie、社区导出、`data_all` 文件都应放在 `local/` 下。
- 由于使用 Commons Clause，本项目是 source-available，但不是 OSI 标准开源许可证项目。

## 环境要求

- Python 3.11 或更高版本。
- WorldQuant BRAIN 账号。
- 主要测试 shell 为 Windows PowerShell。
- 推荐 Conda 环境名：`WQBRAIN`。

## 安装

克隆仓库：

```powershell
git clone https://github.com/untuitivist/wqb_cli.git
cd wqb_cli
```

以 editable 模式安装：

```powershell
conda activate WQBRAIN
python -m pip install -e .
```

确认 CLI 可用：

```powershell
wqb --help
wqb auth status
```

如果 `wqb` 不在 `PATH`，可以从父目录使用 Python 模块方式运行：

```powershell
python -m wqb_cli --help
```

## 包元信息

Python distribution 名称：

```text
wqb-cli
```

Python package/import 名称：

```text
wqb_cli
```

命令行入口：

```powershell
wqb
```

当前版本：

```toml
version = "0.3.1"
```

## 认证

创建本地环境文件：

```powershell
New-Item -ItemType Directory -Force local
Copy-Item .env.example local/.env
```

填写以下任一组账号字段：

```text
EMAIL=...
PASSWORD=...
```

或：

```text
WQB_EMAIL=...
WQB_PASSWORD=...
```

登录：

```powershell
wqb auth login
```

检查认证状态：

```powershell
wqb auth status
```

cookie 保存在：

```text
local/auth/cookies.json
```

不要提交 `local/`、`.env` 或 cookie 文件。

## 仓库结构

```text
.
  cli.py
  commands/                 CLI 命令分组
  core/                     HTTP、认证、配置、registry、IO、本地数据
  resources/
    api_inventory/          随包发布的 API endpoint inventory
    docs/
      commands/             手写命令文档与示例
      generated/            生成的命令参考
  workflow/                 研究流程节点文档
  tests/                    测试套件
  local/                    用户本地运行数据，Git 忽略
  LICENSE
  pyproject.toml
  README.md
  README_CN.md
```

## 常用 API 命令

查看随包 API inventory：

```powershell
wqb api stats
wqb api list
wqb api show /authentication
wqb api params /users/self/alphas
```

调用安全 endpoint：

```powershell
wqb api call GET /authentication
```

查看 simulation options：

```powershell
wqb sim options
```

高层查询命令暴露常用 filter，同时保留 `--param KEY=VALUE` 透传原始 query 参数。

示例：

```powershell
wqb alpha list --settings-neutralization SUBINDUSTRY --is-sharpe ">=1.25"
wqb data fields --dataset analyst14 --coverage ">0.8" --order=-userCount
wqb data datasets --category pv --region USA --delay 1 --limit 20
```

不确定参数时优先看命令帮助：

```powershell
wqb alpha list --help
wqb data datasets --help
wqb data fields --help
wqb data operators --help
wqb sim create --help
```

## Alpha 列表示例

查询某个 region/delay 下近期 ACTIVE REGULAR alpha：

```powershell
wqb alpha list `
  --type REGULAR `
  --settings-region CHN `
  --settings-delay 1 `
  --settings-instrument-type EQUITY `
  --limit 100 `
  --order=-dateSubmitted `
  --status ACTIVE
```

如果已维护塔标签，可以优先用 tag 精确查询：

```powershell
wqb alpha list `
  --type REGULAR `
  --settings-region CHN `
  --settings-delay 1 `
  --settings-instrument-type EQUITY `
  --limit 100 `
  --order=-dateSubmitted `
  --status ACTIVE `
  --tag CHN/D1/PV
```

如果 tag 结果为空或不一致，则退回 region/delay 全量查询，并在本地检查 `pyramids[].name`。

不要依赖 `--param pyramid=pv` 过滤 alpha list。实测服务端会接受这个参数，但不会实际过滤结果。

## 回测流程

从 JSON body 创建 simulation：

```powershell
wqb sim create --input body.json --output simulation_result.json
```

`sim create` 默认等待回测结果或超时失败。multi-simulation 请求会等待并汇总 child simulations。

查询已有 simulation：

```powershell
wqb sim get <simulation_id> --max-wait-seconds 900 --output simulation.json
```

回测示例文档：

```text
resources/docs/commands/simulations/create/examples/input_json.md
resources/docs/commands/simulations/create/examples/backtest_modes.md
```

当前文档覆盖：

- REGULAR FASTEXPR multi-simulation。
- REGULAR FASTEXPR single simulation。
- REGULAR PYTHON single simulation。
- SUPER simulation。

REGULAR FASTEXPR multi-simulation 必须相同的设置范围限定为：

- `delay`
- `region`
- `instrumentType`
- `language`

## Submit 流程

提交 alpha：

```powershell
wqb alpha submit <alpha_id> --output submit_result.json
```

CLI 区分 API 接收成功和最终提交成功：

- `201 Created` 表示提交请求已被 API 接收。
- 最终成功需要继续轮询 submit/check 结果，直到 submit check 成功。
- 如果输出中出现中间状态，应理解为 `201 Created, waiting for results...`。

所有需要等待平台结果的命令都会在最终结果、请求失败或超时后才返回。

## 本地数据配置

本地数据不随仓库发布，也不要提交。

推荐结构：

```text
local/
  .env
  config.json
  auth/
    cookies.json
  community/
    WQPCommunityState_*.json
    WQPCommunityState_*.wqcs
    community.sqlite3
  data_all/
    info_data.bin
    all_data.pickle
    main.ipynb
```

### data_all

`data_all` 来自 WebDataScope 插件提供的网盘数据包：

[leetesla/WebDataScope-WorldQuant](https://github.com/leetesla/WebDataScope-WorldQuant)

`all_data.pickle` 不随本仓库发布。需要从 WebDataScope 插件 README 提供的百度网盘链接单独下载，然后放到：

```text
local/data_all/
```

预期文件：

```text
local/data_all/
  info_data.bin
  all_data.pickle
  main.ipynb
```

检查本地数据：

```powershell
wqb scope files
wqb scope list
wqb scope show USA_1 --output local/scope_usa_1.json
wqb scope top USA_1 --group datafield --min-count 5 --limit 10
wqb scope pickle-summary USA_1 --sample 1
wqb scope alpha-rows USA_1 --table os --datafield volume --limit 3 --columns id,sharpe,fitness,turnover,margin
```

### Community 数据

社区数据来自 WebDataScope 导出。

1. 在 WebDataScope 中导出社区数据，格式为 `WQPCommunityState_*.json` 或 `WQPCommunityState_*.wqcs`。
2. 放到 `local/community/`。
3. 构建本地 SQLite 数据库。
4. 查询生成后的数据库。

构建 SQLite：

```powershell
wqb community export --source local/community/WQPCommunityState_20260520_103908.json
```

如果省略 `--source`，CLI 会在本地 community 目录中寻找最新的 `WQPCommunityState_*.json` 或 `*.wqcs`。

查询示例：

```powershell
wqb community stats
wqb community search alpha --limit 3
wqb community search neutralization --scope docs --limit 2
```

## 研究流程文档

结构化研究流程位于：

```text
workflow/
```

每个节点说明：

- 必要输入
- 允许使用的 CLI
- 必要输出
- 成功条件
- 下一节点

主图：

```text
workflow/workflow_graph.md
```

F 节点负责数据字段可行性。它会优先用 `CHN/D1/PV` 这类塔标签查找已有 ACTIVE REGULAR alpha；如果 tag 不可用或不一致，再退回 region/delay 全量查询，并在本地检查 `pyramids[].name`。

## 命令文档

命令文档位置：

```text
resources/docs/commands/
```

常用入口：

- `resources/docs/commands/README.md`
- `resources/docs/commands/local-data/README.md`
- `resources/docs/commands/community/README.md`
- `resources/docs/commands/scope/README.md`
- `resources/docs/commands/simulations/create/examples/backtest_modes.md`
- `resources/docs/commands/simulations/create/examples/input_json.md`

API inventory：

```text
resources/api_inventory/
```

## 开发

editable 安装：

```powershell
python -m pip install -e .
```

从仓库根目录运行测试：

```powershell
$env:PYTHONPATH='U:\Project\MainCode\3.Work\WQB'
python -m pytest tests
```

构建发布包：

```powershell
python -m build
```

不要提交：

- `.env`
- `local/`
- `dist/`
- `build/`
- `*.egg-info/`
- 凭证或 cookie

## 常见问题

### `ModuleNotFoundError: No module named 'wqb_cli'`

运行测试时把父目录加入 `PYTHONPATH`：

```powershell
$env:PYTHONPATH='U:\Project\MainCode\3.Work\WQB'
python -m pytest tests
```

或重新 editable 安装：

```powershell
python -m pip install -e .
```

### `WARNING: Ignoring invalid distribution ~qb-cli`

通常是 pip 卸载或安装残留在 `site-packages` 中的临时目录。如果安装成功，一般不影响使用。清理时检查当前环境的 `Lib/site-packages`，删除残留的 `~qb*` distribution 目录。

### `wqb.exe is installed ... which is not on PATH`

可以用 Python 模块方式运行，或把提示中的 scripts 目录加入 `PATH`：

```powershell
python -m wqb_cli --help
```

## Release

当前 release：

[wqb-cli 0.3.1](https://github.com/untuitivist/wqb_cli/releases/tag/v0.3.1)

发布 checklist：

1. 更新 `pyproject.toml` 的 `version`。
2. 运行 editable install。
3. 运行测试。
4. 提交改动。
5. 创建 tag，例如 `v0.3.1`。
6. 推送 branch 和 tag。
7. 发布 GitHub Release。

## 许可证

本项目使用 GPL-3.0-only with Commons Clause License Condition v1.0。

必须保留以下署名：

```text
Original author: wiz
Original repository: https://github.com/untuitivist/wqb_cli
Author GitHub: https://github.com/untuitivist
```

Commons Clause 移除了销售本软件的权利，具体定义见 [LICENSE](LICENSE)。这意味着源码可见，但本项目不是 OSI 标准开源项目。
