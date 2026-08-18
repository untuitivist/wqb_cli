# A 认证与运行前检查

## 目标

独立验证本 run 的 `wqb`、认证、`sqlitesimu` 插件和本地持久化路径。A 只做前置检查，不创建候选，不初始化 J 的执行数据库。

## 输入

- WQBRAIN conda 环境。
- 可用的账号配置或 keyring credential。
- 本 run 独立目录。

## 推荐命令

```cmd
wqb --help
wqb auth status > <node_dir>\auth_status.json
wqb auth login
wqb sqlitesimu --help > <node_dir>\sqlitesimu_help.txt
```

只有 `auth status` 未认证时才执行 `auth login`。不得通过直接调用 `requests` 或复制 cookie 绕过 CoreClient。

## 输出

- `run_manifest.json`：写在 run 根目录，`workflow_type` 固定为 `workflow_batchsimu`，`alpha_submission_allowed` 固定为 `false`。
- `auth_status.json`
- `runtime_preflight.json`：Python、wqb-cli、插件可用性和时间戳。
- `storage_plan.json`：J 将使用的绝对数据库路径及是否为本地磁盘。
- `commands.md`
- `node_summary.md`

## 成功条件

- 已认证，`wqb sqlitesimu` 命令存在。
- 数据库计划路径位于当前 run 的 `10_J_sqlite_batch`，且未指向网络共享目录。
- 没有读取或复用其他 run 的可写 SQLite 数据库。

## 下一跳

- `B 批量研究目标`
