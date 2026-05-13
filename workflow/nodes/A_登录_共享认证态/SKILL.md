---
name: 登录-共享认证态
description: 为工作流建立共享认证态。仅用于研究工作图中的第一个节点：触发一次显式登录，把 cookie 写入工作区的共享认证缓存，供后续所有 wqb_core CLI 脚本复用。使用 post_authentication 和 get_authentication。不要在这个节点进入主题、金字塔、数据、alpha 池或回测。
---

# 登录 / 共享认证态

只做一次显式登录，并验证共享认证缓存已经建立。

## 允许使用的工具
- `wqb_core/user/post_authentication.py`
- `wqb_core/user/get_authentication.py`

## 禁止事项
- 不要在这个节点执行主题、金字塔、数据集、字段、alpha 池或回测脚本。
- 不要在这个节点做研究判断。

## 输入
- `RUN_DIR`
  - 本轮研究产物目录。
- 认证来源：
  - 优先使用 `.env`
  - 或运行脚本时显式传 `--username` 和 `--password`

## 标准产物
- `00_auth/post_authentication.json`
- `00_auth/get_authentication.json`
- `00_auth/node_summary.md`

## 成功标准
- `post_authentication` 成功返回。
- `get_authentication` 能读取当前认证状态。
- 工作区下出现或更新：
  - `.wqb_cli_auth/cookies.json`

## 输出要求
`node_summary.md` 至少写清：
- 本节点用了哪些命令
- 是否显式登录成功
- 是否生成了共享 cookie 缓存
- 后续节点是否可以直接复用认证态

## 命令示例
```bat
run.bat "U:\Project\MainCode\3.Work\WQB\wqb_cli\docs\research_runs\2026-05-06_restart_workflow"
```
