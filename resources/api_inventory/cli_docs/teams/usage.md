# CLI 用法: `/teams`

- Methods: `GET`
- Sources: `platform_frontend`
- Description: Teams. / Discovered from platform frontend bundle.

## 查看定义

```powershell
python -m wqb_cli api show "/teams"
```

## 调用方式

### `GET`

Dry-run:

```powershell
python -m wqb_cli api call GET "/teams" --dry-run
```

实际执行:

```powershell
python -m wqb_cli api call GET "/teams"
```

测试记录:

- Status: `tested`
- HTTP: `405 Method Not Allowed`
