# CLI 用法: `/alphas/super-selection`

- Methods: `GET`
- Sources: `platform_frontend`
- Description: Super selection alpha endpoint. / Discovered from platform frontend bundle.

## 查看定义

```powershell
python -m wqb_cli api show "/alphas/super-selection"
```

## 调用方式

### `GET`

Dry-run:

```powershell
python -m wqb_cli api call GET "/alphas/super-selection" --dry-run
```

实际执行:

```powershell
python -m wqb_cli api call GET "/alphas/super-selection"
```

测试记录:

- Status: `tested`
- HTTP: `404 Not Found`
