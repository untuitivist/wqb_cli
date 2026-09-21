# wqb-cli

<p align="center">
  <img src="docs/assets/wqb_cli_logo.png" alt="wqb-cli logo" width="360">
</p>

[English](README.md) | 简体中文

`wqb-cli` 是一个 agent-native 的 WorldQuant BRAIN 命令行工具，用于把认证、API 查询、Alpha 检查、回测执行、Alpha 正式提交、本地数据筛选和社区数据检索组织成可复用的研究流程。

它优先服务编码 agent 和长流程研究 agent，而不是只给人手工敲命令使用的薄封装。命令会输出结构化 JSON，保留原始 API 上下文，等待平台异步结果，并自然适配可重复的研究节点流程。

- 仓库：[untuitivist/wqb_cli](https://github.com/untuitivist/wqb_cli)
- 作者：[wiz](https://github.com/untuitivist)
- 许可证：GPL-3.0-only with Commons Clause，详见 [LICENSE](LICENSE)。

## 常用入口

直接回测命令统一为 `wqb simu`。0.6.1 的示例和脚本使用以下入口：

| 命令 | 用途 |
| --- | --- |
| `wqb simu` | 创建、查询并等待 Regular、Super 和 ALL 回测。 |
| `wqb sqlitesimu` | 候选入库、批量执行、断点恢复和结果导出。 |
| `wqb community` | 在线读帖、搜索，以及带本地图片的 HTML 发帖。 |
| `wqb sqlitecom` | 社区增量同步、本地检索和只读 SQL。 |

查看回测设置和请求帮助可从 `wqb simu options`、`wqb simu create --help` 开始。完整层级见[命令总览](#命令总览)，请求格式见后文示例。

## Agent-Native 设计

`wqb-cli` 的设计目标是让 agent 可以在不依赖浏览器状态、不依赖人工点击的情况下，可检查、可复用、可追踪地操作 BRAIN 工作流：

- 命令输出结构化结果，可用 `--output` 保存，并交给后续 workflow 节点继续使用。
- simulation、submit check、alpha check、recordsets 等异步结果都有明确等待语义。
- 随包提供 API inventory 和命令文档，agent 可以本地检查 endpoint 与参数。
- `workflows/` 下提供两套相互隔离的节点文档，明确输入、允许命令、必要输出和成功条件。
- 本地数据命令读取 `local/` 下的稳定文件，不直接抓取浏览器或插件缓存。
- 命令输出保留 request/response 上下文，包括状态码、参数、Location、retry 事件和返回体。
- `simu create` 和在线 `community` 请求支持显式 `--dry-run` 预览，不登录、不发送 HTTP 请求。

## 功能概览

- 调用 `https://api.worldquantbrain.com` 的 API 命令。
- 登录与 cookie 本地保存。
- REGULAR FASTEXPR、REGULAR PYTHON、SUPER 和 REGION_AGNOSTIC/ALL 回测命令。
- alpha 列表、详情、检查、recordsets、相关性、提交等命令。
- 基于 `data_all` / `all_data.pickle` 的本地字段筛选。
- 在线社区访问、SQLite 增量同步、WebDataScope 数据导入、本地检索与只读 SQL。
- 随包发布的 API endpoint inventory 与命令文档。
- `workflows/` 下的小规模自适应流程与模板群批量流程文档。

## 重要说明

- 本项目不隶属于 WorldQuant 或 WorldQuant BRAIN。
- 会修改平台状态的命令默认发送真实 API 请求；支持 `--dry-run` 的命令只有显式传入该选项才进行预览，运行前可查阅对应帮助。
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

在 WQBRAIN 环境中进行普通安装，得到独立的运行副本：

```powershell
conda activate WQBRAIN
python -m pip install .
```

仓库目录只用于开发和构建发行包。日常命令应在独立研究工作区内，通过 WQBRAIN 环境中的已安装版本运行；不得从开发目录运行，也不得把开发目录加入运行环境的 PYTHONPATH。editable 安装只用于另建的开发环境，不用于 WQBRAIN 运行环境。

切换到研究工作区后，确认已安装 CLI 可用：

```powershell
wqb --help
wqb auth status
```

如果 `wqb` 不在 `PATH`，可以在研究工作区使用当前环境中已安装的模块：

```powershell
python -I -m wqb_cli --help
```

## 命令总览

以下按使用场景排列仓库内置命令，命令名称和层级与实际解析器一致；额外安装的插件可能提供更多入口。`<...>` 表示必填位置参数，`[...]` 表示可选位置参数；命名选项不在树中逐项展开，请通过各层 `--help` 查看。

```text
wqb  # WorldQuant BRAIN 命令行工具
├─ simu                                                          # 平台回测：创建、查询与等待结果
├─ sqlitesimu                                                    # 本地 SQLite 持久化批量回测引擎
├─ alpha                                                         # Alpha 查询、分析、修改与正式提交
├─ data                                                          # 平台数据目录、字段及算子
├─ auth                                                          # 登录与认证会话管理
├─ user                                                          # 当前用户及指定用户的信息与活动
├─ account                                                       # 邮箱、密码和账号令牌接口
├─ consultant                                                    # 顾问信息、顾问计划与说明文档
├─ competition                                                   # 竞赛、规则、排名与 SPC 提交
├─ event                                                         # 平台活动
├─ platform                                                      # 平台公共信息与资源
├─ tutorial                                                      # 平台教程内容
├─ suggest                                                       # 平台建议接口，各项支持 GET/POST
├─ search <query>                                                # 平台全局搜索，没有下一级子命令
├─ community                 # 在线论坛：分区、帖子、评论、搜索和原始 API
├─ sqlitecom                 # 本地社区库：增量同步、查询、导入和只读 SQL
├─ scope                                                         # 按 REGION_DELAY 查看本地历史研究数据
├─ shortcut (alias: quick)                                       # 常用组合操作
├─ config                                                        # 本地配置与平台配置查询
├─ docs                                                          # 查询 CLI 随包文档
├─ api                                                           # 按本地 API 注册表直接调用端点
└─ errors                                                        # 平台错误报告接口
```

<details>
<summary>展开完整命令树（中文说明）</summary>

```text
wqb  # WorldQuant BRAIN 命令行工具
├─ simu                                                          # 平台回测：创建、查询与等待结果
│  ├─ options                                                    # 查看回测设置的可用选项
│  ├─ list                                                       # 查询回测列表
│  ├─ get <simulation_id>                                        # 读取回测状态或结果，支持等待重试
│  ├─ create                                                     # 从 --input 创建回测，并等待结果
│  └─ super-selection                                            # 查询或调用 Super Alpha 选择回测接口
├─ sqlitesimu                                                    # 本地 SQLite 持久化批量回测引擎
│  ├─ init                                                       # 初始化回测数据库
│  ├─ enqueue <input>                                            # 校验 manifest 并入队，不启动执行
│  ├─ run <input>                                                # manifest 入队并执行，支持并发与持久化
│  ├─ resume <run_id>                                            # 恢复已有 run，继续执行未完成工作
│  ├─ status [run_id]                                            # 查看指定 run 或最近多个 run 的状态
│  ├─ cancel <run_id>                                            # 取消本地 run，保留历史记录
│  ├─ export <run_id>                                            # 导出指标、checks、PnL 路径与实验记录
│  ├─ template-validate <input>                                  # 校验模板格式、元数据及候选来源关系
│  └─ template-report <input>                                    # 从 run 导出生成模板分析报告
├─ alpha                                                         # Alpha 查询、分析、修改与正式提交
│  ├─ get <alpha_id>                                             # 获取指定 Alpha 的详情
│  ├─ list                                                       # 查询自己的 Alpha，支持筛选和排序
│  ├─ distribution                                               # 查询 Alpha 分布信息
│  ├─ lists                                                      # 查询平台 Alpha 列表信息
│  ├─ super-selection                                            # 查询 Super Alpha 选择信息
│  ├─ unsubmitted                                                # 查询未提交 Alpha 信息
│  ├─ walkthrough                                                # 获取示例 Alpha 引导信息
│  ├─ all                                                        # 查询 /alphas 接口下的可见 Alpha
│  ├─ check <alpha_id>                                           # 获取平台检查结果，支持等待慢速检查
│  ├─ recordsets <alpha_id>                                      # 列出该 Alpha 可读取的结果数据集
│  ├─ related <alpha_id>                                         # 查询关联 Alpha
│  ├─ recordset <alpha_id> <name>                                # 按名称读取结果，如 pnl、turnover 等
│  ├─ pnl <alpha_id>                                             # 读取 PnL 序列
│  ├─ sharpe <alpha_id>                                          # 读取 Sharpe 结果序列
│  ├─ yearly-stats <alpha_id>                                    # 读取年度统计
│  ├─ patch <alpha_id>                                           # 按 --input 修改 Alpha 属性
│  ├─ submit <alpha_id>                                          # 正式提交 Alpha，并处理提交等待
│  ├─ correlation                                                # 查询 Alpha 相关性
│  │  ├─ self <alpha_id>                                         # 查询自相关检查结果
│  │  ├─ base <alpha_id>                                         # 查询基础相关性接口
│  │  ├─ prod <alpha_id>                                         # 查询生产池相关性
│  │  └─ power-pool <alpha_id>                                   # 查询 Power Pool 相关性
│  └─ performance-comparison <alpha_id>                          # 查询表现比较结果
├─ data                                                          # 平台数据目录、字段及算子
│  ├─ categories                                                 # 查询数据类别
│  ├─ datasets                                                   # 查询数据集列表
│  ├─ dataset <dataset_id>                                       # 查询指定数据集详情
│  ├─ fields                                                     # 查询字段，支持条件筛选
│  ├─ fields-summary                                             # 查询字段汇总信息
│  ├─ dataset-search                                             # 搜索数据集，支持 GET/POST
│  ├─ field <field_id>                                           # 查询指定字段详情
│  └─ operators                                                  # 查询平台算子列表
├─ auth                                                          # 登录与认证会话管理
│  ├─ status                                                     # 查询当前认证状态
│  ├─ head                                                       # 用 HEAD 请求检查认证接口
│  ├─ login                                                      # 登录并保存成功认证后的 cookies
│  ├─ logout                                                     # 注销平台认证会话
│  ├─ brainlabs                                                  # 调用 BrainLabs 认证接口
│  ├─ persona                                                    # 调用 Persona 认证接口
│  ├─ support                                                    # 调用支持站点认证接口
│  └─ workday                                                    # 调用 Workday 认证接口
├─ user                                                          # 当前用户及指定用户的信息与活动
│  ├─ activity <activity_name>                                   # 指定活动的历史记录
│  ├─ osmosis-summary                                            # Osmosis 分配汇总
│  ├─ osmosis-scale-status                                       # Osmosis 积分缩放进度
│  ├─ streak                                                     # 连续活跃记录
│  ├─ tags                                                       # 当前用户标签与列表
│  ├─ submission-activity                                        # 提交活动历史
│  ├─ self                                                       # 获取当前用户资料
│  ├─ consultant-summary                                         # 获取自己的顾问信息摘要
│  ├─ messages                                                   # 查询自己的消息，支持筛选与分页
│  ├─ list                                                       # 查询用户列表
│  ├─ achievements                                               # 查询自己的成就
│  ├─ simulation-activity                                        # 查询自己的回测活动
│  ├─ pyramid-alphas                                             # 查询指定日期范围的金字塔 Alpha 活动
│  ├─ pyramid-multipliers                                        # 查询指定日期范围的金字塔倍率信息
│  ├─ agreements                                                 # 查询自己的协议信息
│  ├─ alphas-summary                                             # 查询自己的 Alpha 汇总
│  ├─ messages-summary                                           # 查询自己的消息摘要
│  ├─ pyramid-alpha-summary                                      # 查询自己的金字塔 Alpha 汇总
│  ├─ teams                                                      # 查询自己的团队
│  ├─ tutorial-steps                                             # 查询自己的教程步骤
│  ├─ tutorial-summary                                           # 查询自己的教程进度摘要
│  ├─ consultant-tutorial-summary                                # 查询自己的顾问教程进度
│  ├─ consultant-tutorial-patch                                  # 修改自己的顾问教程进度
│  ├─ get <user_id>                                              # 获取指定用户资料
│  ├─ user-achievements <user_id>                                # 查询指定用户的成就
│  ├─ user-activities <user_id>                                  # 查询指定用户的活动
│  ├─ user-diversity <user_id>                                   # 按区域、Delay、数据类别查询多样性
│  ├─ user-alphas-options <user_id>                              # 查询用户 Alpha 接口选项，不是列出 Alpha
│  ├─ user-competitions <user_id>                                # 查询指定用户的竞赛信息
│  └─ user-simulation-settings <user_id>                         # 查询指定用户的回测设置
├─ account                                                       # 邮箱、密码和账号令牌接口
│  ├─ email-change                                               # 邮箱修改流程，支持 GET/POST
│  ├─ email-reverify                                             # 邮箱重新验证流程，支持 GET/POST
│  ├─ email-verify                                               # 邮箱验证流程，支持 GET/POST
│  ├─ password-change                                            # 密码修改流程，支持 GET/POST
│  ├─ password-forgot                                            # 忘记密码流程，支持 GET/POST
│  ├─ password-reset                                             # 密码重置流程，支持 GET/POST
│  └─ token                                                      # 账号令牌接口，支持 GET/POST
├─ consultant                                                    # 顾问信息、顾问计划与说明文档
│  ├─ get                                                        # 查询顾问信息
│  ├─ summary                                                    # 查询顾问摘要
│  ├─ datasets                                                   # 查询顾问数据集
│  ├─ dos-and-donts                                              # 读取顾问注意事项
│  ├─ faqs                                                       # 读取顾问常见问题
│  ├─ osmosis-guide                                              # 读取 Osmosis 分配指南
│  ├─ visualization-tool                                         # 读取可视化工具说明
│  ├─ program                                                    # 查询顾问计划信息
│  ├─ program-language <language>                                # 按语言查询顾问计划内容
│  └─ boards                                                     # 顾问榜单
│     └─ leader                                                  # 查询顾问排行榜
├─ competition                                                   # 竞赛、规则、排名与 SPC 提交
│  ├─ list                                                       # 查询竞赛列表
│  ├─ get <competition_id>                                       # 查询指定竞赛详情
│  ├─ agreement <competition_id>                                 # 读取或提交竞赛协议
│  ├─ leaderboard <identifier>                                   # 查询竞赛或顾问排行榜及接口选项
│  ├─ guidelines <competition_id>                                # 读取竞赛规则，实际使用 agreement 接口
│  ├─ faq <competition_id>                                       # 从竞赛详情中读取 FAQ 地址
│  └─ spc                                                        # SPC 提示词提交接口
│     ├─ submissions                                             # 查询提交列表
│     ├─ submission-history <submission_id>                      # 查询指定提交的历史
│     ├─ submission-options [submission_id]                      # 查询提交集合或指定提交的接口选项
│     ├─ create-submission                                       # 新建 SPC 提交
│     └─ update-submission <submission_id>                       # 更新已有 SPC 提交
├─ event                                                         # 平台活动
│  ├─ list                                                       # 查询活动列表
│  ├─ options                                                    # 查询活动接口选项
│  └─ get <event_id>                                             # 查询指定活动详情
├─ platform                                                      # 平台公共信息与资源
│  ├─ achievements                                               # 查询平台成就定义
│  ├─ agreements                                                 # 查询平台协议信息
│  ├─ captcha                                                    # 调用验证码接口
│  ├─ messages                                                   # 查询平台消息接口
│  ├─ tags                                                       # 查询标签
│  ├─ teams                                                      # 查询团队
│  ├─ video-courses                                              # 查询视频课程
│  ├─ achievement-icon <achievement_id>                          # 获取成就图标接口响应
│  └─ competition-level-icon <competition_level_id>              # 获取竞赛等级图标接口响应
├─ tutorial                                                      # 平台教程内容
│  ├─ list                                                       # 查询教程列表
│  ├─ pages                                                      # 查询教程页面列表
│  ├─ page <page_id>                                             # 获取指定教程页面
│  └─ slug <tutorial_slug>                                       # 按教程标识获取教程内容
├─ suggest                                                       # 平台建议接口，各项支持 GET/POST
│  ├─ examples                                                   # 请求示例建议
│  ├─ expression                                                 # 请求表达式建议
│  ├─ fastexpr                                                   # 请求 FASTEXPR 建议
│  └─ fields                                                     # 请求字段建议
├─ search <query>                                                # 平台全局搜索，没有下一级子命令
├─ community                 # 在线论坛：分区、帖子、评论、搜索和原始 API
│  ├─ list / topics / topic / get / comments / search
│  ├─ user-posts / user-comments
│  ├─ create / update / delete / comment-create / comment-update / comment-delete
│  └─ api stats / list / show / params / call
├─ sqlitecom                 # 本地社区库：增量同步、查询、导入和只读 SQL
│  ├─ sync / search / get / import
│  ├─ stats / status / schema
│  └─ sql (alias: query)
├─ scope                                                         # 按 REGION_DELAY 查看本地历史研究数据
│  ├─ files                                                      # 查看本地 scope 数据文件位置
│  ├─ list                                                       # 列出可用范围，例如 USA_1
│  ├─ show <scope>                                               # 查看指定范围摘要
│  ├─ top <scope>                                                # 按历史指标给字段、数据集或类别排序
│  ├─ search <scope> <query>                                     # 搜索范围内的字段、数据集或类别
│  ├─ neutralization <scope>                                     # 查看不同中性化方式的历史表现
│  ├─ pickle-summary <scope>                                     # 读取本地 pickle 中的范围摘要
│  └─ alpha-rows <scope>                                         # 读取历史 Alpha 的属性、设置、IS/OS 行
├─ shortcut (alias: quick)                                       # 常用组合操作
│  ├─ whoami                                                     # 快速检查当前认证会话
│  ├─ simulate                                                   # 创建回测并等待完成
│  ├─ alpha-report <alpha_id>                                    # 汇总详情、检查、相关性与年度统计
│  └─ data-fields                                                # 按区域、Delay、股票池等常用条件查字段
├─ config                                                        # 本地配置与平台配置查询
│  ├─ init                                                       # 初始化本地 CLI 配置文件
│  ├─ list                                                       # 列出本地配置
│  ├─ get <key>                                                  # 获取指定本地配置项
│  ├─ set <key> <value>                                          # 设置本地配置项
│  ├─ set-secret <key> <value>                                   # 将敏感配置存入系统 keyring
│  ├─ platform                                                   # 查询平台配置
│  └─ competition-levels                                         # 查询竞赛等级配置
├─ docs                                                          # 查询 CLI 随包文档
│  ├─ list                                                       # 列出已提供文档的命令节点
│  └─ show <path>                                                # 读取指定文档
├─ api                                                           # 按本地 API 注册表直接调用端点
│  ├─ stats                                                      # 查看本地 API 注册表统计
│  ├─ list                                                       # 列出已登记端点，可按路径前缀筛选
│  ├─ show <path>                                                # 查看指定端点定义
│  ├─ params <path>                                              # 查看查询参数与请求体提示
│  └─ call <method> <path>                                       # 直接调用端点，支持路径变量、参数和 JSON
└─ errors                                                        # 平台错误报告接口
   └─ envelope                                                   # 向平台错误收集接口发送报告
```

</details>

### 如何选择入口

- `simu` 直接调用平台回测接口；`sqlitesimu` 增加本地数据库、批量队列、并发执行、断点恢复和结果导出。
- 回测与正式提交不同：`simu create`、`sqlitesimu run` 发起回测，`alpha submit` 才是正式提交入口。命令树不代表已完成研究流程或提交前终检。
- `community` 读取在线论坛；`sqlitecom` 管理本地社区库，`sync` 通过同一在线客户端增量更新。旧本地查询迁到 `sqlitecom search`，旧导入迁到 `sqlitecom import`。
- `sqlitesimu cancel` 管理本地 run 并保留历史，不等于撤销平台上所有已发出的回测；默认不会越过仍有效的 worker 租约。
- `api call` 可直接调用注册表内端点；写操作会发送真实请求，不会自动补齐高层研究检查。

### 逐层查看帮助

```text
wqb --help
wqb simu --help
wqb simu create --help
wqb alpha correlation --help
wqb alpha correlation prod --help
wqb sqlitesimu run --help
wqb sqlitesimu template-report --help
```

全局选项包括 `--registry` 和 `--cookies`；多数末级命令支持 `--output`。具体筛选、输入文件、等待时间与并发参数，以相应命令的 `--help` 为准。新增、删除或调整命令时，请同步更新两份 README，并用实际解析器核对命令树。

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
version = "0.6.1"
```

## 认证

先定位已安装版本的运行数据目录，再在其中创建或编辑 `.env`；不要把运行凭证写入开发仓库：

```powershell
$WqbLocal = python -I -c "from wqb_cli.core.paths import LOCAL_ROOT; print(LOCAL_ROOT)"
New-Item -ItemType Directory -Force $WqbLocal
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

cookie 保存在已安装包目录下的以下相对位置，而不是当前工作目录下：

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
  workflows/                相互隔离的 simu 与 batchsimu 流程文档
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
wqb simu options
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
wqb simu create --help
```

## API 清单与用户资源更新

2026-09-22 核对 131 个已有及新发现路径，API 目录从 109 条扩展到 127 条。`api list/show/params/call` 可使用新路径及 schema 结构；探测区分只读证据和服务器声明的方法，没有执行写接口，也不打包个人标签等私有选项值。详见[更新报告](resources/api_inventory/reports/api_refresh_20260922.md)。

新增用户命令 `activity <activity_name>`、`osmosis-summary`、`osmosis-scale-status`、`streak`、`tags` 和 `submission-activity`。积分缩放状态正常返回 204 时不再触发重新认证；详见[命令示例](resources/docs/commands/user/README.md)。

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
wqb simu create --input body.json --output simulation_result.json
```

`simu create` 默认等待回测结果或超时失败。multi-simulation 请求会等待并汇总 child simulations。

查询已有 simulation：

```powershell
wqb simu get <simulation_id> --max-wait-seconds 900 --output simulation.json
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

### SQLite 批量回测

`simu`和 `sqlitesimu` 均支持 REGION_AGNOSTIC/ALL：ALL/D1，LARGE、MEDIUM 或 SMALL，单个父请求完成后采集每个地区的子 Alpha 详情和 PnL。官方不支持把 ALL 放入 HTTP batch 数组；SQLite 同一队列可以交错发送单条 ALL 和 Regular 批次，共用派发与服务器背压。

`simu create --dry-run` 预览请求。`sqlitesimu run ... --no-resend` 或 `resume ... --no-resend` 持续收集已受理任务，避免重复 POST。导出新增 `region_agnostic_children`；父 Alpha 不存在独立 PnL，也不按子地区数增加实验数。详见[持久化回测说明](resources/docs/commands/sqlitesimu/README.md)。

工作流只生成批量表达式、由 CLI 独立发起 simulate、轮询、重试和结果入库时：

```powershell
wqb sqlitesimu run candidates.json --output run-result.json
```

需要显式管理进程时，可以初始化数据库、一次性入队，再恢复返回的 run：

```powershell
wqb sqlitesimu init --db simulations.sqlite3
wqb sqlitesimu enqueue candidates.json --db simulations.sqlite3 --output enqueue-result.json
wqb sqlitesimu resume <run_id> --db simulations.sqlite3 --output worker-result.json
wqb sqlitesimu status <run_id> --db simulations.sqlite3 --output status.json
wqb sqlitesimu export <run_id> --db simulations.sqlite3 --output run-export.json
```

默认数据库位于 `local/sqlitesimu/simulations.sqlite3`。每个 run 持久化 candidate、batch、simulation Location、错误、Alpha 详情和 PnL 历史，并提供兼容旧分析代码的 `simued_alpha_is_pnl` 视图。run export 还包含去重日期网格与逐 Alpha 日度增量组成的结构化 `pnl_paths`，供下游相关性分析按日期对齐且不填补缺失值。

模板集 manifest 可以在入队前严格校验，并在 run 终态后生成固定分析报告：

```powershell
wqb sqlitesimu template-validate template-manifest.json --output template-validation.json
wqb sqlitesimu template-report run-export.json --analysis-contract analysis-contract.json --output template-report.json --markdown-output template-report.md
```

分析契约可以把方向无关的 discovery screen 与正向 validation 分开预注册。负向 discovery 只会被标记为需要在新 run 中反向重新 simulate，不能通过变换历史指标直接成为终检候选。

manifest、状态恢复、退出码以及相对旧三个脚本的行为变动见：

```text
resources/docs/sqlitesimu.md
```

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

下文输入数据布局中的 `local/` 指已安装包的运行数据目录，不是开发仓库。可在激活的环境中定位：

```powershell
$WqbLocal = python -I -c "from wqb_cli.core.paths import LOCAL_ROOT; print(LOCAL_ROOT)"
```

从 editable 安装迁移时，应将数据和凭证复制到此目录；升级前备份运行数据。研究输出和 run 数据库保存在独立研究工作区。刷新社区库前必须检查导出覆盖范围；新导出没有文档时，不得因此清空已有文档。

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

`community` 面向在线论坛，`sqlitecom` 面向本地数据库。首次同步可以从空库开始，也能接续插件导入的数据；只合并变化，不覆盖整库或清空官方文档。

```text
wqb community topics
wqb community list --sort updated_at --limit 10
wqb community search wqb_cli --limit 5
wqb community get 41706827651991
wqb community api list
wqb community create --html post.html --title "Research notes" --topic 18910956638743 --dry-run
wqb community create --html post.html --title "Research notes" --topic 18910956638743 --output published.json
wqb sqlitecom sync --sqlite community.sqlite3 --since 2026-09-17 --log sync.log
wqb sqlitecom search --sqlite community.sqlite3 --author JL40454 --scope topics
wqb sqlitecom get 41706827651991 --sqlite community.sqlite3
wqb sqlitecom schema --sqlite community.sqlite3
wqb sqlitecom sql --sqlite community.sqlite3 --file report.sql --param author=JL40454
wqb sqlitecom import --sqlite community.sqlite3 --source export.json
```

`community create --html` 会上传 HTML 目录内的本地图片、替换图片路径、发布正文并回读帖子。保留自动生成的 `.assets.json` 回执，重试时即可复用已上传图片；`--prepared-output` 可保存实际发送的 JSON 正文。`--dry-run` 不发送 HTTP，结果不确定的写请求不会自动重发。JSON 输入、图片限制与改帖命令详见[社区命令文档](resources/docs/commands/community/README.md)。

同步使用游标分页、更新时间边界和默认48小时重叠，断点持久化；`--max-pages` 暂停后再次执行相同命令即可恢复。新库默认建立完整基线，可用 `--since` 限定首次范围。旧评论编辑未必推动父帖更新时间，定期运行 `--reconcile` 复查完整索引；默认7天内检查过且内容未变的帖子会跳过评论下载。

`sql` 支持单条只读 SQL、CTE 和参数绑定，默认最多200行、10秒执行期限；`--file` 从 UTF-8 文件读取，避免命令行转义。数据库使用只读连接并拒绝写入、ATTACH、扩展加载和多语句。其他本地命令不访问网络，只有 `sync` 联网。

## 研究流程文档

`workflows/` 下有两套完整、相互隔离的流程：

```text
workflows/
  workflow_simu/          A-M 小规模自适应研究，同步使用 wqb simu create
  workflow_batchsimu/     A-M 模板群研究，由 sqlitesimu 独立执行回测
```

两套流程各自拥有 A 起点、run 目录、输入输出契约、主图和终止行为，不共享 A-F 产物、SQLite 数据库、节点输入或控制流移交。

入口：

```text
workflows/workflow_simu/workflow_graph.md
workflows/workflow_batchsimu/workflow_graph.md
```

批量流程固定一个 settings cell，对各模板族无放回抽样并保留完整 lineage。只有权威 run 终态后，K 才分析族密度、质量分布、错误类型和真实 IS-PnL 相关性并选择本流候选，L 执行慢速终检，M 是唯一允许调用 `wqb alpha submit` 的节点；候选与结果不会移交给小规模自适应流程。

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

激活运行环境并检查普通安装：

```powershell
conda activate WQBRAIN
python -m pip show wqb-cli
python -I -m wqb_cli --help
```

如果尚未安装，使用实际构建出的 wheel 路径安装：

```powershell
python -m pip install path/to/wqb_cli-version-py3-none-any.whl
```

不要通过把开发目录加入 PYTHONPATH 或在 WQBRAIN 中 editable 安装来修复运行环境。源码测试应在独立开发环境中执行。

### `WARNING: Ignoring invalid distribution ~qb-cli`

通常是 pip 卸载或安装残留在 `site-packages` 中的临时目录。如果安装成功，一般不影响使用。清理时检查当前环境的 `Lib/site-packages`，删除残留的 `~qb*` distribution 目录。

### `wqb.exe is installed ... which is not on PATH`

可以用 Python 模块方式运行，或把提示中的 scripts 目录加入 `PATH`：

```powershell
python -m wqb_cli --help
```

## Release

软件包 release：

[wqb-cli 0.6.1](https://github.com/untuitivist/wqb_cli/releases/tag/v0.6.1)

发布 checklist：

1. 更新 `pyproject.toml` 的 `version`。
2. 运行 editable install。
3. 运行测试。
4. 提交改动。
5. 创建 tag，例如 `v0.6.1`。
6. 推送 branch 和 tag。
7. 发布 GitHub Release。

## 版本记录

以下记录以软件包元数据和 GitHub Release 中出现过的版本为准。原先代码中的 `__version__ = "0.1.0"` 只是未同步的遗留值，从未作为正式软件包版本发布。

### 0.6.1 - 2026-09-22

- 修复实际社区写入的 CSRF；新增 HTML 文件发帖、本地图片上传、可复用图片回执与独立的 API/网页回读验证。本次替换原 v0.6.1 发布资产；已安装 0.6.1 时，安装 wheel 请加 `--force-reinstall --no-cache-dir`。

- 回测入口与源码模块、解析器和文档统一命名为 `wqb simu`；更新已有脚本时使用这一名称。
- 包括 GLB 在内的兼容 Regular 每批最多 10 条，持续派发，遇到平台限流等待后重试。实际回测失败默认重试一次，再失败即记录并跳过；schema 8 持久化失败历史，重启不清空次数。ALL 与 Super 仍按单个对象请求。
- 命中每日回测限额后，暂停新请求至下一个美东零点，自动适应夏令时，重启后仍保留等待时间；已受理的回测和结果继续收集。

### 0.6.0 - 2026-09-22

- 新增：在线 community、独立论坛接口清单、sqlitecom 增量同步与本地查询、参数化只读 SQL。
- 变更：原 community 的本地 search/stats/export 分别迁到 sqlitecom search/stats/import；community search 现在查询在线论坛。
- 认证：沿用 BRAIN 自动续登，并处理论坛 SSO、HTML 跳转与 CSRF；写请求不自动重发。

### 0.5.0 - 2026-09-22

- 新增：simu 与 sqlitesimu 原生 ALL、schema 7 地区子结果、no-resend 与 dry-run、18 条 API 注册路径及用户活动/Osmosis 命令。
- 修复：结果尚未就绪时的 enrichment 处理、端点正常 204 的认证误判；保留 Regular 和 Super 请求形式。
- 此源码/wheel 版本与上方历史 GitHub Release 链接分开记录。

### 0.4.0 - 2026-08-18

- 新增：command-plugin SDK；支持 enqueue/resume/status/cancel/export 的 SQLite 持久化批量回测；模板集 manifest 校验与终态报告；两套物理隔离的 A-M 研究流程。
- 变更：全局 `204/401/429` 会话续期、批量 worker 额外五次重登、服务器 `429 / Retry-After` 背压、轮询优先队列调度，以及 simulate 与 submit 的明确语义区分。
- 保留：不确定的 simulation POST、运行历史、Alpha 详情与 PnL 均保持可审计，不盲目重发或删除。

### 0.3.2 - 2026-07-16

- 新增：通用 competition/consultant 排行榜 scope；比赛 Guidelines 与 FAQ 命令；完整的 SPC prompt submission 列表、创建、历史和更新命令；对应的规范 endpoint inventory、示例和测试。
- 变更：在不移除旧注册项的前提下，完整 API inventory 从 104 个 endpoint、126 个 method case 扩展到 109 个 endpoint、134 个 method case；alpha 请求在 cookie 会话收到 `401` 后可回退 Basic Auth；补强 workflow 运行约束和 README 发布文档；运行时版本与软件包版本保持一致。
- 移除：过时的 analyst/PV vector 示例 JSON 和一份冗余 workflow 文档；没有移除已发布 CLI 命令或已注册 endpoint。

### 0.3.1 - 2026-05-22

- 新增：面向 agent 的 `wqb` 控制台命令；包内 auth/config/community/scope/shortcut 工具；随包 API inventory、生成式命令文档、alpha submit 轮询、冒烟测试、中英文 README 和项目品牌资源。
- 变更：围绕 `wqb_cli` 重建包结构与元数据；扩展 workflow 和本地数据文档；许可证从 MIT 改为 GPL-3.0-only plus Commons Clause。
- 移除：旧的 `wqb_core` package discovery/test 布局和未使用的旧资源。

### 0.2.5 - 2026-05-13

- 新增：最初的软件包化 WorldQuant BRAIN API wrapper 和面向 agent 的 workflow 基线，依赖 `requests`、`pandas`、`msgpack`。
- 变更：无；这是最初的软件包元数据基线。
- 移除：无。

持续维护的完整发布记录见 [CHANGELOG.md](CHANGELOG.md)。

## 许可证

本项目使用 GPL-3.0-only with Commons Clause License Condition v1.0。

必须保留以下署名：

```text
Original author: wiz
Original repository: https://github.com/untuitivist/wqb_cli
Author GitHub: https://github.com/untuitivist
```

Commons Clause 移除了销售本软件的权利，具体定义见 [LICENSE](LICENSE)。这意味着源码可见，但本项目不是 OSI 标准开源项目。
