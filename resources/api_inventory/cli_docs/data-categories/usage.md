# CLI 用法: `/data-categories`

- Methods: `GET`
- Sources: `platform_dynamic_capture, platform_frontend, rocky-d/wqb`
- Description: Data categories. / Discovered from platform frontend bundle.

## 查看定义

```powershell
python -m wqb_cli api show "/data-categories"
```

## 调用方式

### `GET`

Dry-run:

```powershell
python -m wqb_cli api call GET "/data-categories" --dry-run
```

实际执行:

```powershell
python -m wqb_cli api call GET "/data-categories"
```

测试记录:

- Status: `tested`
- HTTP: `200 OK`
