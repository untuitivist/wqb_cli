# CLI 用法: `/users/self`

- Methods: `GET`
- Sources: `rocky-d/wqb`
- Description: Current user profile.

## 查看定义

```powershell
python -m wqb_cli api show "/users/self"
```

## 调用方式

### `GET`

Dry-run:

```powershell
python -m wqb_cli api call GET "/users/self" --dry-run
```

实际执行:

```powershell
python -m wqb_cli api call GET "/users/self"
```

测试记录:

- Status: `tested`
- HTTP: `200 OK`
