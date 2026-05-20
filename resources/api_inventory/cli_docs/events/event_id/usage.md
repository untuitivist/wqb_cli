# CLI 用法: `/events/{event_id}`

- Methods: `GET`
- Sources: `platform_frontend`
- Description: Event details. / Discovered from platform frontend bundle.

## 查看定义

```powershell
python -m wqb_cli api show "/events/{event_id}"
```

## 调用方式

### `GET`

Dry-run:

```powershell
python -m wqb_cli api call GET "/events/{event_id}" --var event_id=zO8y3jm --dry-run
```

实际执行:

```powershell
python -m wqb_cli api call GET "/events/{event_id}" --var event_id=zO8y3jm
```

测试记录:

- Status: `tested`
- HTTP: `200 OK`
