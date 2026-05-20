# CLI 用法: `/tutorial-pages`

- Methods: `GET`
- Sources: `platform_frontend`
- Description: Tutorial pages. / Discovered from platform frontend bundle.

## 查看定义

```powershell
python -m wqb_cli api show "/tutorial-pages"
```

## 调用方式

### `GET`

Dry-run:

```powershell
python -m wqb_cli api call GET "/tutorial-pages" --dry-run
```

实际执行:

```powershell
python -m wqb_cli api call GET "/tutorial-pages"
```

测试记录:

- Status: `tested`
- HTTP: `404 Not Found`
