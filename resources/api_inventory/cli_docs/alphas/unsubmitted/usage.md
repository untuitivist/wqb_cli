# CLI 用法: `/alphas/unsubmitted`

- Methods: `GET`
- Sources: `platform_frontend`
- Description: Unsubmitted alpha endpoint. / Discovered from platform frontend bundle.

## 查看定义

```powershell
python -m wqb_cli api show "/alphas/unsubmitted"
```

## 调用方式

### `GET`

Dry-run:

```powershell
python -m wqb_cli api call GET "/alphas/unsubmitted" --dry-run
```

实际执行:

```powershell
python -m wqb_cli api call GET "/alphas/unsubmitted"
```

测试记录:

- Status: `tested`
- HTTP: `404 Not Found`
