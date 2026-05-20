# CLI 用法: `/alphas/{alpha_id}/alphas`

- Methods: `GET`
- Sources: `platform_frontend`
- Description: Discovered from platform frontend bundle.

## 查看定义

```powershell
python -m wqb_cli api show "/alphas/{alpha_id}/alphas"
```

## 调用方式

### `GET`

Dry-run:

```powershell
python -m wqb_cli api call GET "/alphas/{alpha_id}/alphas" --var alpha_id=vR5p8vqb --dry-run
```

实际执行:

```powershell
python -m wqb_cli api call GET "/alphas/{alpha_id}/alphas" --var alpha_id=vR5p8vqb
```

测试记录:

- Status: `tested`
- HTTP: `404 Not Found`
