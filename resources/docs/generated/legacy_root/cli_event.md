# WQB Event CLI

`wqb event` �?event 相关命令层�?
## `wqb event list`

列出 events�?
Raw API:

```text
GET /events
```

命令:

```powershell
wqb event list --limit 20 --offset 0
```

验证记录:

## `wqb event get`

获取单个 event 详情�?
Raw API:

```text
GET /events/{event_id}
```

命令:

```powershell
wqb event get zO8y3jm
```

验证记录:
