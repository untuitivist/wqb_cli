# A 登录与认证态

## 目标

验证 `wqb` CLI 可用，并建立本轮共享认证态。

## 输入

必要：

- `wqb` 已安装并可执行。
- `wqb_cli/local/.env` 或 keyring 中存在可用账号。

可选：

- 已存在的 `wqb_cli/local/auth/cookies.json`。

## 只允许的 CLI

```powershell
wqb --help
wqb auth status
wqb auth login --execute
wqb auth status
```

## 输出

必要：

- `commands.md`：逐条记录实际执行的 CLI 命令。
- `auth_status.json`：把 `wqb auth status` 的终端 JSON 输出保存为文件；当前该子命令没有 `--output` 参数。
- `node_summary.md`：是否已登录、用户权限、cookie 位置。

可选：

- `login_output.json`：重新登录时保存。

## 成功条件

- `wqb auth status` 返回已认证，后续节点可复用认证态。

## 下一跳

- `B 平台机会与等级差距`
- `C 研究方向与提交额度`
