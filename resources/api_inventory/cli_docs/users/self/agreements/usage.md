# CLI 用法: `/users/self/agreements`

- Methods: `GET`
- Sources: `platform_dynamic_capture`
- Description: Observed by passive platform network capture.

## 查看定义

```powershell
python -m wqb_cli api show "/users/self/agreements"
```

## 调用方式

### `GET`

Dry-run:

```powershell
python -m wqb_cli api call GET "/users/self/agreements" --dry-run
```

实际执行:

```powershell
python -m wqb_cli api call GET "/users/self/agreements"
```

测试记录:

- Status: `tested`
- HTTP: `200 OK`
