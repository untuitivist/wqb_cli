# CLI 用法: `/users`

- Methods: `GET`
- Sources: `platform_frontend`
- Description: Users collection. / Discovered from platform frontend bundle.

## 查看定义

```powershell
python -m wqb_cli api show "/users"
```

## 调用方式

### `GET`

Dry-run:

```powershell
python -m wqb_cli api call GET "/users" --param limit=1 --dry-run
```

实际执行:

```powershell
python -m wqb_cli api call GET "/users" --param limit=1
```

测试记录:

- Status: `tested`
- HTTP: `405 Method Not Allowed`
