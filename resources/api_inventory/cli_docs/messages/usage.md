# CLI 用法: `/messages`

- Methods: `GET`
- Sources: `platform_frontend`
- Description: Message collection. / Discovered from platform frontend bundle.

## 查看定义

```powershell
python -m wqb_cli api show "/messages"
```

## 调用方式

### `GET`

Dry-run:

```powershell
python -m wqb_cli api call GET "/messages" --dry-run
```

实际执行:

```powershell
python -m wqb_cli api call GET "/messages"
```

测试记录:

- Status: `tested`
- HTTP: `404 Not Found`
