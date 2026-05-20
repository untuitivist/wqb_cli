# CLI 用法: `/consultant`

- Methods: `GET`
- Sources: `platform_frontend`
- Description: Consultant landing endpoint. / Discovered from platform frontend bundle.

## 查看定义

```powershell
python -m wqb_cli api show "/consultant"
```

## 调用方式

### `GET`

Dry-run:

```powershell
python -m wqb_cli api call GET "/consultant" --dry-run
```

实际执行:

```powershell
python -m wqb_cli api call GET "/consultant"
```

测试记录:

- Status: `tested`
- HTTP: `404 Not Found`
