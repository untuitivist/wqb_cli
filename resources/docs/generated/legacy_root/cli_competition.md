# WQB Competition CLI

`wqb competition` �?competition 相关命令层�?
## `wqb competition list`

列出 competitions�?
Raw API:

```text
GET /competitions
```

命令:

```powershell
wqb competition list --limit 20 --offset 0
```

验证记录:

## `wqb competition get`

获取单个 competition 详情�?
Raw API:

```text
GET /competitions/{competition_id}
```

命令:

```powershell
wqb competition get challenge
```

验证记录:
