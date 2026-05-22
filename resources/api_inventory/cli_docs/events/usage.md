# CLI 用法: `/events`

- Methods: `GET, OPTIONS`
- Sources: `observed_platform, platform_dynamic_capture, platform_frontend`
- Description: Events list. / Discovered from platform frontend bundle.

## 查看定义

```powershell
python -m wqb_cli api show "/events"
```

## 调用方式

### `GET`

Command:

```powershell
python -m wqb_cli api call GET "/events" --param limit=1
```

实际执行:

```powershell
python -m wqb_cli api call GET "/events" --param limit=1
```

测试记录:

- Status: `tested`
- HTTP: `200 OK`

### `OPTIONS`

Command:

```powershell
python -m wqb_cli api call OPTIONS "/events" --param limit=1
```

实际执行:

```powershell
python -m wqb_cli api call OPTIONS "/events" --param limit=1
```

测试记录:

- Status: `tested`
- HTTP: `200 OK`
