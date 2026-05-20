# CLI 用法: `/configuration`

- Methods: `GET`
- Sources: `platform_dynamic_capture, platform_frontend`
- Description: Platform configuration. / Discovered from platform frontend bundle.

## 查看定义

```powershell
python -m wqb_cli api show "/configuration"
```

## 调用方式

### `GET`

Dry-run:

```powershell
python -m wqb_cli api call GET "/configuration" --dry-run
```

实际执行:

```powershell
python -m wqb_cli api call GET "/configuration"
```

测试记录:

- Status: `tested`
- HTTP: `200 OK`
