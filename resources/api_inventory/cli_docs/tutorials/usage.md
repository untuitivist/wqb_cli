# CLI 用法: `/tutorials`

- Methods: `GET`
- Sources: `observed_platform, platform_frontend`
- Description: Tutorial list. / Discovered from platform frontend bundle.

## 查看定义

```powershell
python -m wqb_cli api show "/tutorials"
```

## 调用方式

### `GET`

Dry-run:

```powershell
python -m wqb_cli api call GET "/tutorials" --param limit=1 --dry-run
```

实际执行:

```powershell
python -m wqb_cli api call GET "/tutorials" --param limit=1
```

测试记录:

- Status: `tested`
- HTTP: `200 OK`
