# CLI 用法: `/authentication/persona`

- Methods: `GET`
- Sources: `platform_frontend`
- Description: Discovered from platform frontend bundle.

## 查看定义

```powershell
python -m wqb_cli api show "/authentication/persona"
```

## 调用方式

### `GET`

Dry-run:

```powershell
python -m wqb_cli api call GET "/authentication/persona" --dry-run
```

实际执行:

```powershell
python -m wqb_cli api call GET "/authentication/persona"
```

测试记录:

- Status: `tested`
- HTTP: `400 Bad Request`
