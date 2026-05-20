# CLI 用法: `/alphas/sample-alpha-id-walkthrough`

- Methods: `GET`
- Sources: `platform_frontend`
- Description: Discovered from platform frontend bundle.

## 查看定义

```powershell
python -m wqb_cli api show "/alphas/sample-alpha-id-walkthrough"
```

## 调用方式

### `GET`

Dry-run:

```powershell
python -m wqb_cli api call GET "/alphas/sample-alpha-id-walkthrough" --dry-run
```

实际执行:

```powershell
python -m wqb_cli api call GET "/alphas/sample-alpha-id-walkthrough"
```

测试记录:

- Status: `tested`
- HTTP: `404 Not Found`
