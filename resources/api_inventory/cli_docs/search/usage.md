# CLI 用法: `/search`

- Methods: `GET`
- Sources: `platform_frontend`
- Description: Global search. / Discovered from platform frontend bundle.

## 查看定义

```powershell
python -m wqb_cli api show "/search"
```

## 调用方式

### `GET`

Dry-run:

```powershell
python -m wqb_cli api call GET "/search" --dry-run
```

实际执行:

```powershell
python -m wqb_cli api call GET "/search"
```

测试记录:

- Status: `tested`
- HTTP: `400 Bad Request`
