# WQB User CLI

`wqb user` 是用户与账号状态相关命令层�?
## `wqb user self`

获取当前登录用户资料�?
Raw API:

```text
GET /users/self
```

命令:

```powershell
wqb user self
```

验证记录:

## `wqb user consultant-summary`

获取当前用户 consultant performance summary�?
Raw API:

```text
GET /users/self/consultant/summary
```

命令:

```powershell
wqb user consultant-summary
```

验证记录:

## `wqb user messages`

获取当前用户消息列表�?
Raw API:

```text
GET /users/self/messages
```

命令:

```powershell
wqb user messages --limit 20 --offset 0
```

验证记录:
