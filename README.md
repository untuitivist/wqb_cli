# WQB CLI

`wqb` 是面向 agent 使用的 WorldQuant BRAIN 命令行工具。
它把能力分成两类：

- API 命令：调用 `https://api.worldquantbrain.com`。
- 本地数据命令：读取 `local/` 下的本地文件。

本地数据由 WebDataScope 浏览器插件在本包之外产生：[leetesla/WebDataScope-WorldQuant](https://github.com/leetesla/WebDataScope-WorldQuant)。
CLI 不直接读取浏览器缓存或插件缓存。

## 仓库结构

```text
.
  cli.py
  commands/                 命令分组
  core/                     HTTP、认证、配置、注册表、IO、本地数据
  resources/
    api_inventory/          随包发布的 API 端点注册表与生成文档
    docs/
      commands/             手写命令文档与真实示例
      generated/            生成说明
  tests/                    CLI 冒烟测试
  local/                    用户本地运行数据，Git 忽略
  pyproject.toml
```

Python 包名仍然是 `wqb_cli`。
`pyproject.toml` 将 `wqb_cli` 映射到当前仓库根目录。

## 安装

要求 Python 3.11 或更高版本。
当前本地工作流使用 Conda 环境 `WQBRAIN`。

```powershell
conda activate WQBRAIN
python -m pip install -e .
```

## 认证

创建本地 `.env` 文件：

```powershell
Copy-Item .env.example local/.env
```

填写 `EMAIL` / `PASSWORD` 或 `WQB_EMAIL` / `WQB_PASSWORD`。

登录：

```powershell
wqb auth login
```

Cookie 存储位置：

```text
local/auth/cookies.json
```

## API 命令

API 命令使用随包发布的注册表：

```text
resources/api_inventory/api_inventory_complete.json
```

示例：

```powershell
wqb api stats
wqb api list
wqb api show /authentication
wqb api params /users/self/alphas
wqb api call GET /authentication
wqb auth status
wqb sim options
```

常用查询命令显式建模了相邻 `U:\Project\MainCode\3.Work\WQB\wqb` SDK 中已使用的过滤参数，也保留 `--param KEY=VALUE` 透传兜底，例如：

```powershell
wqb alpha list --settings-neutralization SUBINDUSTRY --is-sharpe ">=1.25"
wqb data fields --dataset analyst14 --coverage ">0.8" --order=-userCount
```

这些显式参数的 `--help` 文档里写了本地 `U:\Project\MainCode\3.Work\WQB` 工作流中常用的取值和阈值示例。
需要确认参数怎么填时，优先看命令帮助：

```powershell
wqb alpha list --help
wqb data datasets --help
wqb data fields --help
wqb data operators --help
```

会修改平台状态的命令会直接发送请求。

## 本地数据导入

本地数据不随包发布，也不能提交到 Git。
所有本地数据都放在 `local/` 下。

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

`data_all` 来自 WebDataScope 插件提供的网盘数据包。
单独下载后，将文件直接放到：

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

使用 `scope` 命令检查：

```powershell
wqb scope files
wqb scope list
wqb scope top USA_1 --group datafield --min-count 5 --limit 10
wqb scope pickle-summary USA_1 --sample 1
wqb scope alpha-rows USA_1 --table os --datafield volume --limit 3 --columns id,sharpe,fitness,turnover,margin
```

### community

社区数据由 WebDataScope 导出文件构建。
流程如下：

1. 在 WebDataScope 中导出社区数据，格式为 `WQPCommunityState_*.json` 或 `WQPCommunityState_*.wqcs`。
2. 将导出文件放到 `local/community/`。
3. 运行 `wqb community export` 生成 `community.sqlite3`。
4. 查询生成后的 SQLite 数据库。

构建 SQLite：

```powershell
wqb community export --source local/community/WQPCommunityState_20260520_103908.json
```

如果省略 `--source`，CLI 会在本地导出位置中寻找最新的 `WQPCommunityState_*.json` 或 `*.wqcs`。

查询示例：

```powershell
wqb community stats
wqb community search alpha --limit 3
wqb community search neutralization --scope docs --limit 2
```

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

API 清单文档位置：

```text
resources/api_inventory/
```

## 回测规则

回测模式与并发规则记录在：

```text
resources/docs/commands/simulations/create/examples/backtest_modes.md
```

当前操作约束：

- `REGULAR_FASTEXPR_MULTI` 单次请求最多支持 10 条表达式。
- `REGULAR_FASTEXPR_MULTI` 建议批量大小：`region != "GLB"` 时为 10，`region == "GLB"` 时为 5。
- `REGULAR_PYTHON` 不能使用 multi-simulation。
- `SUPER` 每次 simulation 使用一个 SUPER POST body。
- `SUPER` 并发 simulation 请求最多 3 个。
- `REGULAR` 并发 simulation 请求：`region != "GLB"` 时最多 8 个，`region == "GLB"` 时最多 4 个。

## 开发

运行冒烟测试：

```powershell
python -m unittest discover -s tests
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
