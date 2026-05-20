# CLI 用法: `/agreements`

- Methods: `GET`
- Sources: `platform_frontend`
- Description: Agreements. / Discovered from platform frontend bundle.

## 查看定义

```powershell
python -m wqb_cli api show "/agreements"
```

## 调用方式

### `GET`

Dry-run:

```powershell
python -m wqb_cli api call GET "/agreements" --dry-run
```

实际执行:

```powershell
python -m wqb_cli api call GET "/agreements"
```

测试记录:

- Status: `tested`
- HTTP: `405 Method Not Allowed`
