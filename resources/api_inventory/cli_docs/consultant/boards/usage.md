# CLI 用法: `/consultant/boards`

- Methods: `GET`
- Sources: `platform_frontend`
- Description: Consultant boards. / Discovered from platform frontend bundle.

## 查看定义

```powershell
python -m wqb_cli api show "/consultant/boards"
```

## 调用方式

### `GET`

Dry-run:

```powershell
python -m wqb_cli api call GET "/consultant/boards" --dry-run
```

实际执行:

```powershell
python -m wqb_cli api call GET "/consultant/boards"
```

测试记录:

- Status: `tested`
- HTTP: `404 Not Found`
